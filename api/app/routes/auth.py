from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.http_schemas.auth import (
    AuthMessageResponse,
    RegisterRequest,
    RegistrationConfigResponse,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    SessionResponse,
    SessionResolveResponse,
)
from app.config import get_settings
from app.core.auth import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME, verify_access_token, verify_refresh_token
from app.services.auth import AuthService
from app.core.deps import get_optional_current_user
from app.models.user import User
from app.services.turnstile import TurnstileRejected, verify_turnstile

router = APIRouter()
settings = get_settings()

AUTH_COOKIE_PATH = "/"
LEGACY_ACCESS_COOKIE_PATH = "/api/v1"
LEGACY_REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = settings.environment == "production"
    response.delete_cookie(ACCESS_COOKIE_NAME, path=LEGACY_ACCESS_COOKIE_PATH)
    response.delete_cookie(REFRESH_COOKIE_NAME, path=LEGACY_REFRESH_COOKIE_PATH)
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        access_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path=AUTH_COOKIE_PATH,
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path=AUTH_COOKIE_PATH,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE_NAME, path=AUTH_COOKIE_PATH)
    response.delete_cookie(REFRESH_COOKIE_NAME, path=AUTH_COOKIE_PATH)
    # Remove cookies issued by the pre-Start Vite deployment. Keeping these
    # cleanup entries for one release lets an already-authenticated browser
    # migrate without retaining two path-scoped values with the same name.
    response.delete_cookie(ACCESS_COOKIE_NAME, path=LEGACY_ACCESS_COOKIE_PATH)
    response.delete_cookie(REFRESH_COOKIE_NAME, path=LEGACY_REFRESH_COOKIE_PATH)


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(
    request: Request,
    response: Response,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        await verify_turnstile(body.turnstile_token)
    except TurnstileRejected as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security verification failed",
        ) from exc

    service = AuthService(db)
    try:
        await service.register(body)
        return None
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered") from exc


@router.get("/registration-config", response_model=RegistrationConfigResponse)
async def registration_config():
    required = not (settings.turnstile_bypass and settings.environment in {"development", "test"})
    return RegistrationConfigResponse(
        turnstile_site_key=settings.turnstile_site_key if required and settings.turnstile_configured else None,
        turnstile_required=required,
        turnstile_action=settings.turnstile_expected_action,
    )


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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from exc


@router.post("/logout", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def logout(
    request: Request,
    response: Response,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    email = current_user.email if current_user else verify_refresh_token(raw_refresh_token or "")
    service = AuthService(db)
    if email:
        await service.logout(email, raw_refresh_token)
    _clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.get("/session", response_model=SessionResponse)
@limiter.limit("60/minute")
async def session(
    request: Request,
    response: Response,
    current_user: User | None = Depends(get_optional_current_user),
):
    return SessionResponse(
        authenticated=current_user is not None,
        account_tier=current_user.account_tier if current_user is not None else None,
    )


@router.post("/resolve", response_model=SessionResolveResponse)
@limiter.limit("60/minute")
async def resolve_session(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Resolve the browser session once for a server-rendered page request.

    The endpoint intentionally returns a safe session snapshot only. If the
    short-lived access cookie is expired, it rotates the refresh cookie and
    returns the newly resolved account in the same response. Raw tokens never
    cross the Start/server-render boundary.
    """

    service = AuthService(db)
    access_token = request.cookies.get(ACCESS_COOKIE_NAME)
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    had_auth_cookies = bool(access_token or refresh_token)
    access_email = verify_access_token(access_token or "") if access_token else None
    if access_email:
        current_user = await service.get_user_by_email(access_email)
        if current_user:
            return SessionResolveResponse(
                authenticated=True,
                account_tier=current_user.account_tier,
                refreshed=False,
            )

    if refresh_token:
        try:
            new_access_token, new_refresh_token = await service.refresh(refresh_token)
            _set_auth_cookies(response, new_access_token, new_refresh_token)
            refreshed_email = verify_access_token(new_access_token)
            current_user = (
                await service.get_user_by_email(refreshed_email)
                if refreshed_email
                else None
            )
            if current_user:
                return SessionResolveResponse(
                    authenticated=True,
                    account_tier=current_user.account_tier,
                    refreshed=True,
                )
        except ValueError:
            # A stale or concurrently rotated refresh cookie is an anonymous
            # session from the page renderer's perspective. Clear every known
            # cookie path so the browser can recover with a fresh login.
            pass

    if had_auth_cookies:
        _clear_auth_cookies(response)
    return SessionResolveResponse(authenticated=False, account_tier=None, refreshed=False)
