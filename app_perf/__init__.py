"""
Performance optimization module for Agency Project Builder
Provides Fast2 TF-IDF analysis and SSE streaming
"""

from .fast_pipeline import router as fast_router
from .stream import router as stream_router

__all__ = ['fast_router', 'stream_router']