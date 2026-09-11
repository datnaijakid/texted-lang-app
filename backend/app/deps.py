from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import decode_token
from app import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_token_from_request(
    request: Request,
    header_token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[str]:
    # 1. Prefer explicit Authorization Header if provided
    if header_token:
        return header_token

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]

    # 2. Check Secure HttpOnly Cookie
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        if cookie_token.startswith("Bearer "):
            return cookie_token[7:]
        return cookie_token

    return None


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(get_token_from_request),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or session expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    user_id = decode_token(token)
    if user_id is None:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user


def get_current_verified_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """Ensure the user has verified their email address before accessing core learning/AI features."""
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address not verified. Please verify your email to proceed.",
        )
    return current_user
