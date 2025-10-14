"""
SQLite Embedding Cache for Performance Optimization
Caches OpenAI embeddings to avoid re-computing the same text
"""

import sqlite3
import hashlib
import json
import threading
import os
from typing import List, Optional
import numpy as np

# Configuration from environment
_EMBED_DB_PATH = os.getenv("EMBED_DB", "/tmp/embed_cache.sqlite3")
_EMBED_DB_LOCK = threading.Lock()

def _embed_db():
    """Create/connect to embedding cache database"""
    conn = sqlite3.connect(_EMBED_DB_PATH, check_same_thread=False, timeout=10)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embeds (
                key TEXT PRIMARY KEY,
                text_hash TEXT NOT NULL,
                model TEXT NOT NULL,
                vec BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Create index for faster lookups
        conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON embeds(model)")
    return conn

def _hash_text(t: str) -> str:
    """Generate deterministic hash of text"""
    return hashlib.sha256((t or "").encode("utf-8")).hexdigest()

def _get_cached_embed(conn, model: str, text: str) -> Optional[List[float]]:
    """Retrieve cached embedding if exists"""
    key = f"{model}:{_hash_text(text)}"
    row = conn.execute("SELECT vec FROM embeds WHERE key=?", (key,)).fetchone()
    if row:
        return json.loads(row[0])
    return None

def _put_cached_embed(conn, model: str, text: str, vec: List[float]):
    """Store embedding in cache"""
    key = f"{model}:{_hash_text(text)}"
    text_hash = _hash_text(text)
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO embeds(key,text_hash,model,vec) VALUES(?,?,?,?)",
            (key, text_hash, model, json.dumps(vec))
        )

def embed_many(texts: List[str], model: str = "text-embedding-3-large", client=None) -> List[List[float]]:
    """
    Embed multiple texts with caching.
    Returns list of embedding vectors.
    
    Args:
        texts: List of strings to embed
        model: OpenAI embedding model to use
        client: OpenAI client instance (will create if None)
    
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    # Connect to cache
    conn = _embed_db()
    pending = []
    out = [None] * len(texts)
    
    # 1) Check cache for each text
    cache_hits = 0
    for i, t in enumerate(texts):
        cached = _get_cached_embed(conn, model, t)
        if cached is None:
            pending.append((i, t))
        else:
            out[i] = cached
            cache_hits += 1
    
    if cache_hits > 0:
        print(f"[EMBED CACHE] {cache_hits}/{len(texts)} cache hits")
    
    # 2) Fetch missing embeddings in batches
    if pending:
        print(f"[EMBED CACHE] Computing {len(pending)} new embeddings")
        
        # Create client if not provided
        if client is None:
            from openai import OpenAI
            client = OpenAI()
        
        BATCH_SIZE = 256  # OpenAI's recommended batch size
        
        for b in range(0, len(pending), BATCH_SIZE):
            chunk = pending[b:b+BATCH_SIZE]
            idxs = [i for (i, _) in chunk]
            payload = [t for (_, t) in chunk]
            
            if not payload:
                continue
                
            try:
                # Call OpenAI embeddings API
                response = client.embeddings.create(
                    model=model,
                    input=payload
                )
                
                # Store results and cache them
                for j, data in zip(idxs, response.data):
                    vec = data.embedding
                    out[j] = vec
                    _put_cached_embed(conn, model, texts[j], vec)
                    
            except Exception as e:
                print(f"[EMBED CACHE] Error computing embeddings: {e}")
                # Return partial results if available
                raise
    
    conn.close()
    return out

def embed_single(text: str, model: str = "text-embedding-3-large", client=None) -> List[float]:
    """
    Embed a single text with caching.
    
    Args:
        text: String to embed
        model: OpenAI embedding model to use
        client: OpenAI client instance
        
    Returns:
        Embedding vector
    """
    result = embed_many([text], model, client)
    return result[0] if result else []

def clear_cache():
    """Clear the entire embedding cache"""
    conn = _embed_db()
    with conn:
        conn.execute("DELETE FROM embeds")
    conn.close()
    print(f"[EMBED CACHE] Cache cleared")

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