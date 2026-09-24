"""
Local username/password auth for MODE=local.
Uses bcrypt hashing + JWT session tokens.
"""
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import jwt, JWTError
from app.config import settings

# bcrypt context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings for local mode
LOCAL_JWT_SECRET = "genomicsops-local-secret-change-me"  # overridden on first run
LOCAL_JWT_ALGORITHM = "HS256"
LOCAL_TOKEN_EXPIRE_HOURS = 24 * 7  # 1 week


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(password, password_hash)
    except Exception:
        return False


def create_token(user_id: str, role: str) -> str:
    """Create a JWT for local sessions."""
    payload = {
        "sub": user_id,
        "role": role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=LOCAL_TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, LOCAL_JWT_SECRET, algorithm=LOCAL_JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT. Returns payload or None."""
    try:
        return jwt.decode(token, LOCAL_JWT_SECRET, algorithms=[LOCAL_JWT_ALGORITHM])
    except JWTError:
        return None
