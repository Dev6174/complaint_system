# pyrefly: ignore [missing-import]
import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, HTTPException, status
from app.config import settings

# In-memory storage for rate limiting: key -> list of epoch timestamps
_rate_limit_cache: Dict[str, List[float]] = defaultdict(list)

def is_rate_limited(key: str, max_requests: int, window_seconds: int) -> bool:
    """
    Checks if a key (IP or user ID) has exceeded rate limits.
    """
    now = time.time()
    timestamps = _rate_limit_cache[key]
    
    # Filter out timestamps older than the window
    expired_limit = now - window_seconds
    timestamps = [t for t in timestamps if t > expired_limit]
    _rate_limit_cache[key] = timestamps
    
    if len(timestamps) >= max_requests:
        return True
        
    _rate_limit_cache[key].append(now)
    return False

def rate_limit_ip(max_requests: int = 60, window_seconds: int = 60):
    """
    Dependency to rate limit requests by IP address.
    """
    def dependency(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        key = f"ip:{client_ip}:{request.url.path}"
        if is_rate_limited(key, max_requests, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later."
            )
    return dependency

def rate_limit_user(max_requests: int = 5, window_seconds: int = 60):
    """
    Enforces per-account rate limits. Call manually in routes using user identifiers.
    """
    def check_limit(identifier: str):
        key = f"user:{identifier}"
        if is_rate_limited(key, max_requests, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Account activity limit exceeded. Please wait a minute."
            )
    return check_limit

def reset_rate_limiter():
    """
    Clears the rate limiter database/cache for test runs.
    """
    _rate_limit_cache.clear()

