# ai_port.py
# Future-proof abstraction layer for AI planner
# Allows switching between in-process and HTTP sidecar implementations in <1 hour

from typing import Protocol, Dict
import httpx

class AIPlanner(Protocol):
    """Protocol defining the AI planner interface"""
    async def analyze(self, request_text: str, strictness: str = "balanced") -> Dict:
        """Analyze request text and return summary + suggestions"""
        ...

class InprocPlanner:
    """In-process implementation using ai_planner_integrated module"""
    def __init__(self):
        from ai_planner_integrated import analyze_text
        self._analyze_fn = analyze_text
    
    async def analyze(self, request_text: str, strictness: str = "balanced") -> Dict:
        """Call the integrated planner directly (synchronous wrapped as async)"""
        # The analyze_text function is synchronous, so we just call it
        return self._analyze_fn(request_text, strictness)

class HttpPlanner:
    """HTTP client implementation for sidecar microservice"""
    def __init__(self, base_url: str = "http://localhost:5050"):
        self.base_url = base_url.rstrip("/")
    
    async def analyze(self, request_text: str, strictness: str = "balanced") -> Dict:
        """Call remote AI planner via HTTP"""
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{self.base_url}/analyze",
                json={"request_text": request_text, "strictness": strictness}
            )
            response.raise_for_status()
            return response.json()

# Factory function to create the appropriate planner
def create_ai_planner(use_http: bool = False, http_base_url: str = "http://localhost:5050") -> AIPlanner:
    """
    Create an AI planner instance.
    
    Args:
        use_http: If True, use HTTP sidecar. If False, use in-process planner.
        http_base_url: Base URL for HTTP sidecar (only used if use_http=True)
    
    Returns:
        AIPlanner instance (either InprocPlanner or HttpPlanner)
    """
    if use_http:
        return HttpPlanner(base_url=http_base_url)
    else:
        return InprocPlanner()
