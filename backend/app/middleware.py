"""
Security middleware: HSTS, CSP, X-Frame-Options, etc.
Plus a lightweight in-memory rate limiter.
"""
import time
from collections import defaultdict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter.
    Key = client IP + endpoint path prefix.
    Limit: 120 requests / 60 seconds.
    """
    def __init__(self, app, limit: int = 120, window: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Skip docs, health, and CORS preflight
        path = request.url.path
        if path.startswith(("/docs", "/redoc", "/openapi", "/health")):
            return await call_next(request)
        if request.method == "OPTIONS":
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        key = f"{client}:{path.split('/')[1] if path != '/' else '/'}"

        now = time.time()
        cutoff = now - self.window
        self.hits[key] = [t for t in self.hits[key] if t > cutoff]

        if len(self.hits[key]) >= self.limit:
            return JSONResponse(
                {"detail": "Rate limit exceeded. Try again shortly."},
                status_code=429,
            )

        self.hits[key].append(now)
        return await call_next(request)
