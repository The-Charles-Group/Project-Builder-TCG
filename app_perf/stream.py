"""
Server-Sent Events (SSE) streaming for real-time progress updates
Fixes the 0% progress bar issue by streaming updates immediately
"""

import json
import asyncio
import time
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from dataclasses import dataclass
from enum import Enum

router = APIRouter()

# Job states for SSE streaming
class StreamJobStatus(str, Enum):
    QUEUED = "queued"
    INITIALIZING = "initializing"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class StreamJob:
    """Job state for SSE streaming"""
    job_id: str
    status: StreamJobStatus
    progress: float = 0.0
    message: str = ""
    total_items: int = 0
    processed_items: int = 0
    current_stage: str = ""
    eta_seconds: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    start_time: float = 0.0
    
    def to_sse_event(self) -> str:
        """Convert job state to SSE event format"""
        data = {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": round(self.progress, 1),
            "message": self.message,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "current_stage": self.current_stage,
            "eta_seconds": round(self.eta_seconds, 1) if self.eta_seconds else None,
            "elapsed_seconds": round(time.time() - self.start_time, 1) if self.start_time else 0
        }
        
        # Include result only if completed
        if self.status == StreamJobStatus.COMPLETED and self.result:
            data["result"] = self.result
        
        # Include error if failed
        if self.status == StreamJobStatus.FAILED and self.error:
            data["error"] = self.error
        
        return f"data: {json.dumps(data)}\n\n"

# Global job store for SSE streaming (separate from main job store)
SSE_JOB_STORE: Dict[str, StreamJob] = {}

def update_sse_job(job_id: str, **kwargs):
    """Update SSE job state"""
    if job_id in SSE_JOB_STORE:
        job = SSE_JOB_STORE[job_id]
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)
        
        # Recalculate progress if items are updated
        if job.total_items > 0:
            job.progress = (job.processed_items / job.total_items) * 100
        
        # Calculate ETA if processing
        if job.status == StreamJobStatus.PROCESSING and job.processed_items > 0:
            elapsed = time.time() - job.start_time
            avg_time_per_item = elapsed / job.processed_items
            remaining = job.total_items - job.processed_items
            job.eta_seconds = remaining * avg_time_per_item

def create_sse_job(job_id: str, total_items: int = 0) -> StreamJob:
    """Create a new SSE job"""
    job = StreamJob(
        job_id=job_id,
        status=StreamJobStatus.QUEUED,
        total_items=total_items,
        start_time=time.time(),
        message="Job created, preparing to start..."
    )
    SSE_JOB_STORE[job_id] = job
    return job

async def sse_event_generator(job_id: str, check_main_store: bool = True):
    """
    Generate SSE events for a job with improved heartbeat mechanism
    check_main_store: If True, also check the main AI_JOB_STORE for updates
    """
    # Send initial event immediately to fix 0% issue
    yield f"data: {json.dumps({'status': 'connected', 'job_id': job_id})}\n\n"
    
    last_update = None
    last_heartbeat_time = time.time()
    no_change_count = 0
    max_no_change = 1200  # Stop after 20 minutes of no changes (increased for large projects)
    heartbeat_interval = 2  # Send heartbeat every 2 seconds for better connection monitoring
    
    while no_change_count < max_no_change:
        try:
            current_time = time.time()
            should_send_heartbeat = (current_time - last_heartbeat_time) >= heartbeat_interval
            
            # Check SSE job store first
            if job_id in SSE_JOB_STORE:
                job = SSE_JOB_STORE[job_id]
                event = job.to_sse_event()
                
                # Send update if changed, or send heartbeat if needed
                if event != last_update:
                    yield event
                    last_update = event
                    last_heartbeat_time = current_time
                    no_change_count = 0
                elif should_send_heartbeat:
                    # Send explicit heartbeat to keep connection alive
                    heartbeat_event = f"data: {json.dumps({'type': 'heartbeat', 'job_id': job_id, 'status': job.status.value, 'progress': job.progress, 'timestamp': current_time})}\n\n"
                    yield heartbeat_event
                    last_heartbeat_time = current_time
                    # Don't reset no_change_count for heartbeats
                else:
                    no_change_count += 1
                
                # Stop if job is complete
                if job.status in [StreamJobStatus.COMPLETED, StreamJobStatus.FAILED, StreamJobStatus.CANCELLED]:
                    # Send final event with result
                    yield event
                    # Clean up after a delay
                    asyncio.create_task(cleanup_sse_job(job_id, delay=60))
                    break
            
            # Also check main AI_JOB_STORE if requested
            elif check_main_store:
                # Import here to avoid circular dependency
                try:
                    from ai_planner_agencydb import AI_JOB_STORE, AIJobStatus
                    
                    if job_id in AI_JOB_STORE:
                        ai_job = AI_JOB_STORE[job_id]
                        
                        # Convert to SSE format
                        status_map = {
                            AIJobStatus.PENDING: StreamJobStatus.QUEUED,
                            AIJobStatus.RUNNING: StreamJobStatus.PROCESSING,
                            AIJobStatus.COMPLETED: StreamJobStatus.COMPLETED,
                            AIJobStatus.FAILED: StreamJobStatus.FAILED
                        }
                        
                        # Calculate progress
                        progress = 0.0
                        if ai_job.total_chunks > 0:
                            progress = (ai_job.processed_chunks / ai_job.total_chunks) * 100
                        
                        # Create event data
                        event_data = {
                            "job_id": job_id,
                            "status": status_map.get(ai_job.status, StreamJobStatus.PROCESSING).value,
                            "progress": round(progress, 1),
                            "message": ai_job.current_stage,
                            "total_items": ai_job.total_chunks,
                            "processed_items": ai_job.processed_chunks,
                            "current_stage": ai_job.current_stage
                        }
                        
                        # Include result if completed
                        if ai_job.status == AIJobStatus.COMPLETED and ai_job.result:
                            event_data["result_preview"] = {
                                "item_count": len(ai_job.result.get("items", [])) if isinstance(ai_job.result, dict) else 0
                            }
                        
                        event = f"data: {json.dumps(event_data)}\n\n"
                        
                        # Send update if changed, or send heartbeat if needed
                        if event != last_update:
                            yield event
                            last_update = event
                            last_heartbeat_time = current_time
                            no_change_count = 0
                        elif should_send_heartbeat:
                            # Send heartbeat for AI job
                            heartbeat_event = f"data: {json.dumps({'type': 'heartbeat', 'job_id': job_id, 'status': event_data['status'], 'progress': event_data['progress'], 'timestamp': current_time})}\n\n"
                            yield heartbeat_event
                            last_heartbeat_time = current_time
                        else:
                            no_change_count += 1
                        
                        # Stop if complete
                        if ai_job.status in [AIJobStatus.COMPLETED, AIJobStatus.FAILED]:
                            yield event
                            break
                    else:
                        # Job not found in either store - send heartbeat if needed
                        if should_send_heartbeat:
                            heartbeat_event = f"data: {json.dumps({'type': 'heartbeat', 'job_id': job_id, 'status': 'searching', 'timestamp': current_time})}\n\n"
                            yield heartbeat_event
                            last_heartbeat_time = current_time
                        no_change_count += 1
                except ImportError:
                    # AI planner not available - send heartbeat if needed
                    if should_send_heartbeat:
                        heartbeat_event = f"data: {json.dumps({'type': 'heartbeat', 'job_id': job_id, 'status': 'waiting', 'timestamp': current_time})}\n\n"
                        yield heartbeat_event
                        last_heartbeat_time = current_time
                    no_change_count += 1
            else:
                # Job not found - send heartbeat if needed
                if should_send_heartbeat:
                    heartbeat_event = f"data: {json.dumps({'type': 'heartbeat', 'job_id': job_id, 'status': 'waiting', 'timestamp': current_time})}\n\n"
                    yield heartbeat_event
                    last_heartbeat_time = current_time
                no_change_count += 1
            
            # Wait before next check
            await asyncio.sleep(1)
            
        except Exception as e:
            error_event = f"data: {json.dumps({'error': str(e), 'job_id': job_id})}\n\n"
            yield error_event
            break
    
    # Send timeout event if we stopped due to no changes
    if no_change_count >= max_no_change:
        yield f"data: {json.dumps({'status': 'timeout', 'message': 'No updates for 20 minutes', 'job_id': job_id})}\n\n"

async def cleanup_sse_job(job_id: str, delay: int = 60):
    """Clean up SSE job after a delay"""
    await asyncio.sleep(delay)
    if job_id in SSE_JOB_STORE:
        del SSE_JOB_STORE[job_id]
        print(f"[SSE] Cleaned up job {job_id}")

@router.get("/api/stream/{job_id}")
async def stream_job_progress(job_id: str):
    """
    Stream job progress updates via Server-Sent Events
    Fixes 0% progress issue by sending immediate updates
    """
    # Check if job exists in either store
    job_exists = False
    
    # Check SSE store
    if job_id in SSE_JOB_STORE:
        job_exists = True
    else:
        # Check main AI job store
        try:
            from ai_planner_agencydb import AI_JOB_STORE
            if job_id in AI_JOB_STORE:
                job_exists = True
        except ImportError:
            pass
    
    if not job_exists:
        # Try the general job store from sitecustomize
        try:
            import sitecustomize
            if hasattr(sitecustomize, '_JOBS') and job_id in sitecustomize._JOBS:
                job_exists = True
        except (ImportError, AttributeError):
            pass
    
    if not job_exists:
        raise HTTPException(404, f"Job {job_id} not found")
    
    return StreamingResponse(
        sse_event_generator(job_id, check_main_store=True),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        }
    )

@router.post("/api/stream/test")
async def create_test_stream():
    """Create a test SSE job for debugging"""
    import uuid
    
    job_id = uuid.uuid4().hex[:12]
    job = create_sse_job(job_id, total_items=100)
    
    # Simulate progress updates
    async def simulate_progress():
        await asyncio.sleep(1)
        update_sse_job(job_id, status=StreamJobStatus.INITIALIZING, message="Initializing test job...")
        
        await asyncio.sleep(2)
        update_sse_job(job_id, status=StreamJobStatus.PROCESSING, message="Processing items...")
        
        for i in range(1, 101):
            update_sse_job(job_id, processed_items=i, message=f"Processing item {i}/100")
            await asyncio.sleep(0.1)  # Simulate work
        
        update_sse_job(job_id, 
                      status=StreamJobStatus.COMPLETED,
                      message="Test completed successfully",
                      result={"test": "success"})
    
    # Start simulation in background
    asyncio.create_task(simulate_progress())
    
    return {"job_id": job_id, "stream_url": f"/api/stream/{job_id}"}

@router.get("/api/stream/jobs")
async def list_sse_jobs():
    """List all active SSE jobs (for debugging)"""
    jobs = []
    for job_id, job in SSE_JOB_STORE.items():
        jobs.append({
            "job_id": job_id,
            "status": job.status.value,
            "progress": round(job.progress, 1),
            "message": job.message,
            "elapsed": round(time.time() - job.start_time, 1) if job.start_time else 0
        })
    
    return {"jobs": jobs, "total": len(jobs)}