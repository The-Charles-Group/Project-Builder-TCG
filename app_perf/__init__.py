"""
Performance optimization module for Agency Project Builder
Provides Fast2 TF-IDF analysis and SSE streaming with job lifecycle stages
"""

from .fast_pipeline import router as fast_router
from .stream import (
    router as stream_router,
    StreamJobStatus,
    StreamJobType,
    StreamJob,
    SSE_JOB_STORE,
    JOB_LIFECYCLE_STAGES,
    create_sse_job,
    update_sse_job,
    advance_sse_stage,
    complete_sse_job,
    fail_sse_job,
    get_sse_job,
)

__all__ = [
    'fast_router',
    'stream_router',
    'StreamJobStatus',
    'StreamJobType',
    'StreamJob',
    'SSE_JOB_STORE',
    'JOB_LIFECYCLE_STAGES',
    'create_sse_job',
    'update_sse_job',
    'advance_sse_stage',
    'complete_sse_job',
    'fail_sse_job',
    'get_sse_job',
]