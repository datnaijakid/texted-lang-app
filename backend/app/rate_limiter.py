import time
from collections import defaultdict
from typing import Tuple, Dict, List
from fastapi import Request, HTTPException, status

# In-memory sliding window rate limiter: IP -> route_prefix -> list of timestamps
_request_records: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))

RATE_LIMIT_RULES: List[Tuple[str, int, int]] = [
    ("/api/auth/login", 10, 60),
    ("/api/auth/register", 5, 60),
    ("/api/auth/verify-email", 10, 60),
    ("/api/auth/resend-verification", 3, 60),
    ("/api/auth/forgot-password", 3, 60),
    ("/api/auth/reset-password", 5, 60),
]


def clear_rate_limits() -> None:
    """Clear in-memory rate limit records (useful for test runs)."""
    _request_records.clear()


def check_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path
    now = time.time()

    for prefix, max_reqs, window in RATE_LIMIT_RULES:
        if path == prefix or path.startswith(prefix):
            timestamps = _request_records[client_ip][prefix]
            cutoff = now - window
            _request_records[client_ip][prefix] = [t for t in timestamps if t > cutoff]
            if len(_request_records[client_ip][prefix]) >= max_reqs:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded for {prefix}. Please wait a moment before trying again.",
                )
            _request_records[client_ip][prefix].append(now)
            break
