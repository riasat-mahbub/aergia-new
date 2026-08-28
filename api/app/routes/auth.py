from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.schemas.auth import (
    AuthMessageResponse,
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    ChangePasswordRequest,
)
from app.config import get_settings
from app.core.auth import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME
from app.services.auth import AuthService
from app.core.deps import get_current_user, get_optional_current_user
from app.models.user import User

router = APIRouter()
settings = get_settings()


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = settings.environment == "production"
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        access_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/api/v1",
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/api/v1/auth",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/api/v1")
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/api/v1/auth")


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    try:
        await service.register(body)
        return None
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered") from exc


@router.post("/login", response_model=TokenResponse | AuthMessageResponse)
@limiter.limit("10/minute")
async def login(request: Request, response: Response, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    try:
        access_token, refresh_token, _ = await service.login(body)
        _set_auth_cookies(response, access_token, refresh_token)
        if settings.expose_tokens_in_response:
            return TokenResponse(access_token=access_token, refresh_token=refresh_token)
        return AuthMessageResponse(message="Logged in")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password") from exc


@router.post("/refresh", response_model=TokenResponse | AuthMessageResponse)
@limiter.limit("10/minute")
async def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    try:
        raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
        if settings.allow_bearer_tokens and body is not None:
            raw_refresh_token = body.refresh_token
        if not raw_refresh_token:
            raise ValueError("missing refresh token")
        access_token, refresh_token = await service.refresh(raw_refresh_token)
        _set_auth_cookies(response, access_token, refresh_token)
        if settings.expose_tokens_in_response:
            return TokenResponse(access_token=access_token, refresh_token=refresh_token)
        return AuthMessageResponse(message="Session refreshed")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token") from exc


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    await service.logout(current_user.email)
    _clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    response: Response,
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    try:
        await service.change_password(current_user.email, body.old_password, body.new_password)
        response.delete_cookie(REFRESH_COOKIE_NAME, path="/api/v1/auth")
        return {"message": "Password changed successfully"}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid current password") from exc


@router.get("/session")
async def session(current_user: User | None = Depends(get_optional_current_user)):
    return {"authenticated": current_user is not None}
