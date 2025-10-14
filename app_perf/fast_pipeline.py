"""
Fast2 TF-IDF pipeline for ultra-fast deliverable analysis
No GPT-5 calls, pure TF-IDF matching with varied confidence scores
Target: <2 seconds for text-only RFPs
"""

import os
import time
import json
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from .utils import TFIDFAnalyzer, get_cached_analyzer, save_analyzer_cache, create_db_hash

router = APIRouter()

# Global analyzer instance (will be populated on first use or at startup)
_tfidf_analyzer: Optional[TFIDFAnalyzer] = None
_db_hash: Optional[str] = None

class Fast2Request(BaseModel):
    """Request model for Fast2 analysis"""
    text: str
    mode: str = "fast2"
    
class Fast2Response(BaseModel):
    """Response model for Fast2 analysis"""
    items: List[Dict[str, Any]]
    mode: str = "fast2"
    processing_time_ms: float
    confidence_distribution: Dict[str, int]

def initialize_analyzer(app_state: Any = None):
    """
    Initialize the TF-IDF analyzer with database documents
    Can be called at startup or on first request
    """
    global _tfidf_analyzer, _db_hash
    
    # Try to get database from app state
    if app_state and hasattr(app_state, 'db'):
        db = app_state.db
        if db and hasattr(db, 'all_rows'):
            # Create documents from database rows
            documents = []
            seen = set()
            
            # Convert DataFrame to records for easier iteration
            for _, row in db.all_rows.iterrows():
                # Access columns from pandas Series/row
                deliv_code = row.get('Deliverable_Code', '') if 'Deliverable_Code' in row else ''
                deliv_name = row.get('Deliverable', '') if 'Deliverable' in row else ''
                component = row.get('Component', '') if 'Component' in row else ''
                task = row.get('Task', '') if 'Task' in row else ''
                service_dept = row.get('Service_Department', '') if 'Service_Department' in row else ''
                
                # Create unique key for deduplication
                key = f"{deliv_code}_{component}_{task}"
                if key in seen or not deliv_code:
                    continue
                seen.add(key)
                
                documents.append({
                    'code': str(deliv_code),
                    'deliverable': str(deliv_name),
                    'component': str(component),
                    'task': str(task),
                    'service_dept': str(service_dept),
                })
            
            # Create hash for caching
            _db_hash = create_db_hash(documents)
            
            # Try to load from cache first
            _tfidf_analyzer = get_cached_analyzer(_db_hash)
            
            if not _tfidf_analyzer:
                # Build new analyzer
                print(f"[Fast2] Building TF-IDF index for {len(documents)} documents...")
                start = time.time()
                _tfidf_analyzer = TFIDFAnalyzer(documents)
                elapsed = (time.time() - start) * 1000
                print(f"[Fast2] Index built in {elapsed:.1f}ms")
                
                # Save to cache
                save_analyzer_cache(_tfidf_analyzer, _db_hash)
            
            return True
    
    return False

@router.post("/api/ai/analyze_fast2", response_model=Fast2Response)
async def analyze_fast2(request: Request, req: Fast2Request):
    """
    Ultra-fast TF-IDF analysis endpoint
    Returns deliverables with varied confidence scores in <2 seconds
    """
    start_time = time.time()
    
    # Validate input
    if not req.text or len(req.text.strip()) < 10:
        raise HTTPException(400, "Text must be at least 10 characters")
    
    # Initialize analyzer if needed (lazy loading)
    if not _tfidf_analyzer:
        app_state = request.app.state if hasattr(request.app, 'state') else None
        if not initialize_analyzer(app_state):
            raise HTTPException(500, "Failed to initialize TF-IDF analyzer")
    
    # Analyze the RFP text
    results = _tfidf_analyzer.analyze_rfp(req.text, top_k=80)
    
    # Convert to expected format with enhanced metadata
    items = []
    confidence_buckets = {
        '90-100': 0, '80-90': 0, '70-80': 0,
        '60-70': 0, '50-60': 0, '40-50': 0, '<40': 0
    }
    
    deliverable_groups = {}
    
    for r in results:
        confidence = r['confidence']
        
        # Track confidence distribution
        if confidence >= 90:
            confidence_buckets['90-100'] += 1
        elif confidence >= 80:
            confidence_buckets['80-90'] += 1
        elif confidence >= 70:
            confidence_buckets['70-80'] += 1
        elif confidence >= 60:
            confidence_buckets['60-70'] += 1
        elif confidence >= 50:
            confidence_buckets['50-60'] += 1
        elif confidence >= 40:
            confidence_buckets['40-50'] += 1
        else:
            confidence_buckets['<40'] += 1
        
        # Group by deliverable code for component aggregation
        code = r['code']
        if code not in deliverable_groups:
            deliverable_groups[code] = {
                'code': code,
                'deliverable': r['deliverable'],
                'confidence': confidence,
                'relevance': r['relevance'],
                'components': [],
                'level': 'deliverable'
            }
        
        # Add component if present
        if r.get('component'):
            deliverable_groups[code]['components'].append({
                'name': r['component'],
                'confidence': confidence
            })
    
    # Convert to items list
    for code, group in deliverable_groups.items():
        # Calculate average confidence if there are components
        if group['components']:
            comp_confidences = [c['confidence'] for c in group['components']]
            avg_confidence = sum(comp_confidences) / len(comp_confidences)
            group['confidence'] = round(avg_confidence, 1)
        
        items.append({
            'code': group['code'],
            'name': group['deliverable'],
            'confidence': group['confidence'],
            'relevance': group['relevance'],
            'level': 'deliverable',
            'dept': 'General',  # Can be enhanced with department mapping
            'reasoning': f"TF-IDF match score: {group['relevance']}%"
        })
    
    # Sort by confidence
    items.sort(key=lambda x: x['confidence'], reverse=True)
    
    # Take top 50 for response
    items = items[:50]
    
    processing_time = (time.time() - start_time) * 1000
    
    print(f"[Fast2] Processed in {processing_time:.1f}ms, returned {len(items)} deliverables")
    print(f"[Fast2] Confidence distribution: {confidence_buckets}")
    
    return Fast2Response(
        items=items,
        mode="fast2",
        processing_time_ms=processing_time,
        confidence_distribution=confidence_buckets
    )

@router.get("/api/ai/fast2/status")
async def get_fast2_status():
    """Check if Fast2 analyzer is initialized and ready"""
    return {
        "initialized": _tfidf_analyzer is not None,
        "document_count": len(_tfidf_analyzer.documents) if _tfidf_analyzer else 0,
        "vocabulary_size": len(_tfidf_analyzer.vocabulary) if _tfidf_analyzer else 0,
        "cache_hash": _db_hash
    }

@router.post("/api/ai/fast2/warmup")
async def warmup_fast2(request: Request):
    """Warmup the Fast2 analyzer by pre-building the index"""
    app_state = request.app.state if hasattr(request.app, 'state') else None
    
    if initialize_analyzer(app_state):
        return {"status": "success", "message": "Fast2 analyzer warmed up"}
    else:
        raise HTTPException(500, "Failed to warmup Fast2 analyzer")