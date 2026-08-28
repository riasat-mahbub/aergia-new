from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.config import get_settings
from app.core.auth import ACCESS_COOKIE_NAME, verify_access_token
from app.services.auth import AuthService
from app.models.user import User

settings = get_settings()
security = HTTPBearer(auto_error=False)
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if settings.allow_bearer_tokens and credentials:
        token = credentials.credentials
    email = verify_access_token(token) if token else None
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    auth_service = AuthService(db)
    user = await auth_service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if settings.allow_bearer_tokens and credentials:
        token = credentials.credentials
    if not token:
        return None
    email = verify_access_token(token)
    if not email:
        return None
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_email(email)
    return user
