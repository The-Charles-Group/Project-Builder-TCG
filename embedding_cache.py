"""
SQLite Embedding Cache for Performance Optimization with Session Isolation
Caches OpenAI embeddings to avoid re-computing the same text
Supports session-scoped caching to prevent data contamination between RFPs
"""

import sqlite3
import hashlib
import json
import threading
import os
import time
from typing import List, Optional
import numpy as np

# Configuration from environment
_EMBED_DB_PATH = os.getenv("EMBED_DB", "/tmp/embed_cache.sqlite3")
_EMBED_DB_LOCK = threading.Lock()
_CACHE_TTL_SECONDS = int(os.getenv("EMBED_CACHE_TTL", "86400"))  # 24 hours default
_CACHE_MAX_SIZE_MB = int(os.getenv("EMBED_CACHE_MAX_SIZE", "500"))  # 500MB default

def _embed_db():
    """Create/connect to embedding cache database with session support"""
    conn = sqlite3.connect(_EMBED_DB_PATH, check_same_thread=False, timeout=10)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embeds (
                key TEXT PRIMARY KEY,
                session_id TEXT,
                text_hash TEXT NOT NULL,
                model TEXT NOT NULL,
                vec BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)
        # Create indexes for faster lookups
        conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON embeds(model)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON embeds(session_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON embeds(expires_at)")
    return conn

def _hash_text(t: str) -> str:
    """Generate deterministic hash of text"""
    return hashlib.sha256((t or "").encode("utf-8")).hexdigest()

def _cleanup_expired(conn):
    """Remove expired cache entries"""
    current_time = time.time()
    with conn:
        result = conn.execute(
            "DELETE FROM embeds WHERE expires_at IS NOT NULL AND expires_at < ?",
            (current_time,)
        )
        deleted = result.rowcount
        if deleted > 0:
            print(f"[EMBED CACHE] Cleaned up {deleted} expired entries")

def _enforce_size_limit(conn):
    """Enforce cache size limit by removing oldest entries"""
    db_size = os.path.getsize(_EMBED_DB_PATH) if os.path.exists(_EMBED_DB_PATH) else 0
    max_size_bytes = _CACHE_MAX_SIZE_MB * 1024 * 1024
    
    if db_size > max_size_bytes:
        # Delete oldest 20% of entries
        total = conn.execute("SELECT COUNT(*) FROM embeds").fetchone()[0]
        to_delete = int(total * 0.2)
        
        with conn:
            conn.execute("""
                DELETE FROM embeds WHERE key IN (
                    SELECT key FROM embeds ORDER BY created_at ASC LIMIT ?
                )
            """, (to_delete,))
        print(f"[EMBED CACHE] Size limit exceeded, deleted {to_delete} oldest entries")

def _get_cached_embed(conn, model: str, text: str, session_id: Optional[str] = None) -> Optional[List[float]]:
    """Retrieve cached embedding if exists (session-scoped - NO FALLBACK to prevent contamination)"""
    text_hash = _hash_text(text)
    
    # Session-specific cache lookup (strict isolation - no global fallback)
    if session_id:
        key = f"{session_id}:{model}:{text_hash}"
        row = conn.execute(
            "SELECT vec, expires_at FROM embeds WHERE key=? AND (expires_at IS NULL OR expires_at > ?)",
            (key, time.time())
        ).fetchone()
        if row:
            return json.loads(row[0])
        # CRITICAL FIX: Do NOT fallback to global cache when session_id provided
        # This prevents old RFP data from contaminating new sessions
        return None
    
    # Only use global cache when NO session_id provided (legacy support)
    key = f"{model}:{text_hash}"
    row = conn.execute(
        "SELECT vec, expires_at FROM embeds WHERE key=? AND session_id IS NULL AND (expires_at IS NULL OR expires_at > ?)",
        (key, time.time())
    ).fetchone()
    if row:
        return json.loads(row[0])
    
    return None

def _put_cached_embed(conn, model: str, text: str, vec: List[float], session_id: Optional[str] = None):
    """Store embedding in cache (session-scoped with TTL)"""
    text_hash = _hash_text(text)
    
    if session_id:
        key = f"{session_id}:{model}:{text_hash}"
    else:
        key = f"{model}:{text_hash}"
    
    expires_at = time.time() + _CACHE_TTL_SECONDS if _CACHE_TTL_SECONDS > 0 else None
    
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO embeds(key,session_id,text_hash,model,vec,expires_at) VALUES(?,?,?,?,?,?)",
            (key, session_id, text_hash, model, json.dumps(vec), expires_at)
        )

def embed_many(texts: List[str], model: str = "text-embedding-3-large", client=None, session_id: Optional[str] = None) -> List[List[float]]:
    """
    Embed multiple texts with caching (session-scoped).
    Returns list of embedding vectors.
    
    Args:
        texts: List of strings to embed
        model: OpenAI embedding model to use
        client: OpenAI client instance (will create if None)
        session_id: Optional session ID for cache isolation
    
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    # Connect to cache
    conn = _embed_db()
    
    # Cleanup expired entries and enforce size limits periodically
    _cleanup_expired(conn)
    _enforce_size_limit(conn)
    
    pending = []
    out = [None] * len(texts)
    
    # 1) Check cache for each text (session-scoped)
    cache_hits = 0
    for i, t in enumerate(texts):
        cached = _get_cached_embed(conn, model, t, session_id)
        if cached is None:
            pending.append((i, t))
        else:
            out[i] = cached
            cache_hits += 1
    
    if cache_hits > 0:
        session_log = f" [session: {session_id}]" if session_id else ""
        print(f"[EMBED CACHE] {cache_hits}/{len(texts)} cache hits{session_log}")
    
    # 2) Fetch missing embeddings in batches
    if pending:
        session_log = f" [session: {session_id}]" if session_id else ""
        print(f"[EMBED CACHE] Computing {len(pending)} new embeddings{session_log}")
        
        # Create client if not provided
        if client is None:
            from openai import OpenAI
            client = OpenAI()
        
        # Token-based chunking to avoid exceeding context limits
        MAX_TOKENS = 4000  # More conservative limit to prevent errors (8192 max, keep large buffer)
        MAX_BATCH_SIZE = 50  # Reduced max items per batch to prevent token overflow
        
        def estimate_tokens(text):
            # More conservative estimate: 1 token per 3 characters (safer)
            # This prevents underestimating tokens which causes the 8318 token error
            return len(text) / 3
        
        # Group texts into batches that don't exceed token limit
        batches = []
        current_batch = []
        current_tokens = 0
        
        for idx, text in pending:
            text_tokens = estimate_tokens(text)
            
            # If single text exceeds limit, truncate it
            if text_tokens > MAX_TOKENS:
                print(f"[EMBED CACHE] Warning: Text {idx} exceeds token limit, truncating...")
                # Truncate to approximately MAX_TOKENS * 4 characters
                text = text[:int(MAX_TOKENS * 4)]
                text_tokens = estimate_tokens(text)
            
            # Check if adding this text would exceed limits
            if (current_tokens + text_tokens > MAX_TOKENS or 
                len(current_batch) >= MAX_BATCH_SIZE) and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0
            
            current_batch.append((idx, text))
            current_tokens += text_tokens
        
        if current_batch:
            batches.append(current_batch)
        
        print(f"[EMBED CACHE] Processing {len(batches)} batches...")
        
        for batch_num, batch in enumerate(batches, 1):
            idxs = [i for (i, _) in batch]
            payload = [t for (_, t) in batch]
            
            if not payload:
                continue
                
            try:
                # Call OpenAI embeddings API
                response = client.embeddings.create(
                    model=model,
                    input=payload
                )
                
                # Store results and cache them (session-scoped)
                for j, data in zip(idxs, response.data):
                    vec = data.embedding
                    out[j] = vec
                    _put_cached_embed(conn, model, texts[j], vec, session_id)
                    
                if batch_num % 5 == 0:
                    print(f"[EMBED CACHE] Processed batch {batch_num}/{len(batches)}")
                    
            except Exception as e:
                print(f"[EMBED CACHE] Error in batch {batch_num}: {e}")
                # Try to process items individually if batch fails
                if "context length" in str(e).lower():
                    print(f"[EMBED CACHE] Retrying batch {batch_num} with smaller chunks...")
                    for idx, text in batch:
                        try:
                            # Process individually with truncation if needed
                            truncated_text = text[:8000] if len(text) > 8000 else text
                            response = client.embeddings.create(
                                model=model,
                                input=[truncated_text]
                            )
                            vec = response.data[0].embedding
                            out[idx] = vec
                            _put_cached_embed(conn, model, truncated_text, vec, session_id)
                        except Exception as inner_e:
                            print(f"[EMBED CACHE] Failed to embed text {idx}: {inner_e}")
                            # Use zero vector as fallback
                            out[idx] = [0.0] * 1536  # Default dimension for text-embedding-3-large
                else:
                    raise
    
    conn.close()
    return out

def embed_single(text: str, model: str = "text-embedding-3-large", client=None, session_id: Optional[str] = None) -> List[float]:
    """
    Embed a single text with caching (session-scoped).
    
    Args:
        text: String to embed
        model: OpenAI embedding model to use
        client: OpenAI client instance
        session_id: Optional session ID for cache isolation
        
    Returns:
        Embedding vector
    """
    result = embed_many([text], model, client, session_id)
    return result[0] if result else []

def clear_cache(session_id: Optional[str] = None):
    """Clear embedding cache (all or session-specific)"""
    conn = _embed_db()
    with conn:
        if session_id:
            result = conn.execute("DELETE FROM embeds WHERE session_id = ?", (session_id,))
            deleted = result.rowcount
            print(f"[EMBED CACHE] Cleared {deleted} entries for session: {session_id}")
        else:
            conn.execute("DELETE FROM embeds")
            print(f"[EMBED CACHE] Cleared entire cache")

def get_cache_stats():
    """Get statistics about the cache"""
    conn = _embed_db()
    stats = {}
    
    # Total embeddings
    total = conn.execute("SELECT COUNT(*) FROM embeds").fetchone()[0]
    stats['total_embeddings'] = total
    
    # By model
    model_counts = conn.execute(
        "SELECT model, COUNT(*) FROM embeds GROUP BY model"
    ).fetchall()
    stats['by_model'] = {model: count for model, count in model_counts}
    
    # Cache size
    db_size = os.path.getsize(_EMBED_DB_PATH) if os.path.exists(_EMBED_DB_PATH) else 0
    stats['cache_size_mb'] = round(db_size / (1024 * 1024), 2)
    
    conn.close()
    return stats

# Test function
if __name__ == "__main__":
    # Test the cache
    test_texts = [
        "digital marketing campaign",
        "social media strategy",
        "digital marketing campaign",  # Duplicate - should hit cache
    ]
    
    print("Testing embedding cache...")
    embeddings = embed_many(test_texts)
    print(f"Got {len(embeddings)} embeddings")
    
    stats = get_cache_stats()
    print(f"Cache stats: {stats}")