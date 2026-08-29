from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select, update

from app.models.user import User
from app.core.auth import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    hash_token,
    refresh_token_expires_at,
    verify_password,
    verify_token_hash,
)
from app.schemas.auth import RegisterRequest, LoginRequest
from app.models.auth_session import AuthSession


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, request: RegisterRequest) -> User:
        existing = await self.db.execute(select(User).where(User.email == request.email))
        if existing.scalar_one_or_none():
            raise ValueError("Email already registered")

        user = User(
            email=request.email,
            password_hash=hash_password(request.password),
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def login(self, request: LoginRequest) -> tuple[str, str, User]:
        result = await self.db.execute(select(User).where(User.email == request.email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(request.password, user.password_hash):
            raise ValueError("Invalid email or password")

        session_id = str(uuid4())
        access_token = create_access_token(user.email, session_id=session_id)
        refresh_token = create_refresh_token(user.email, session_id=session_id)
        # Clear the legacy single-session value if this database has not yet
        # completed its first post-migration refresh.
        user.refresh_token_hash = None
        self.db.add(
            AuthSession(
                id=session_id,
                user_id=user.id,
                refresh_token_hash=hash_token(refresh_token),
                expires_at=refresh_token_expires_at(),
            )
        )
        await self.db.flush()
        return access_token, refresh_token, user

    async def refresh(self, raw_refresh_token: str) -> tuple[str, str]:
        claims = decode_refresh_token(raw_refresh_token)
        if not claims:
            raise ValueError("Invalid or expired refresh token")
        email = claims["sub"]

        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        old_hash = hash_token(raw_refresh_token)
        raw_session_id = claims.get("sid") or claims.get("jti")
        session_id = raw_session_id if isinstance(raw_session_id, str) else None
        session = None
        if session_id:
            session_result = await self.db.execute(
                select(AuthSession)
                .where(AuthSession.id == session_id, AuthSession.user_id == user.id)
                .with_for_update()
            )
            session = session_result.scalar_one_or_none()

        # Support one legacy token during migration. Its JWT jti becomes the
        # new session ID, then all subsequent rotations use AuthSession.
        if session is None and user.refresh_token_hash and verify_token_hash(raw_refresh_token, user.refresh_token_hash):
            exp = claims.get("exp")
            if not isinstance(exp, (int, float)) or not session_id:
                raise ValueError("Invalid or expired refresh token")
            expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
            session = AuthSession(
                id=session_id,
                user_id=user.id,
                refresh_token_hash=old_hash,
                expires_at=expires_at,
            )
            self.db.add(session)
            user.refresh_token_hash = None
            await self.db.flush()

        if (
            session is None
            or session.revoked_at is not None
            or not verify_token_hash(raw_refresh_token, session.refresh_token_hash)
        ):
            raise ValueError("Refresh token has been revoked")

        new_access_token = create_access_token(user.email, session_id=session.id)
        new_refresh_token = create_refresh_token(user.email, session_id=session.id)
        rotated = await self.db.execute(
            update(AuthSession)
            .where(
                and_(
                    AuthSession.id == session.id,
                    AuthSession.user_id == user.id,
                    AuthSession.refresh_token_hash == old_hash,
                    AuthSession.revoked_at.is_(None),
                )
            )
            .values(
                refresh_token_hash=hash_token(new_refresh_token),
                last_used_at=datetime.now(timezone.utc),
            )
        )
        if rotated.rowcount != 1:
            raise ValueError("Invalid or expired refresh token")
        await self.db.flush()
        return new_access_token, new_refresh_token

    async def logout(self, email: str, raw_refresh_token: str | None = None) -> None:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            return

        if raw_refresh_token:
            claims = decode_refresh_token(raw_refresh_token)
            session_id = claims.get("sid") if claims else None
            if isinstance(session_id, str):
                await self.db.execute(
                    update(AuthSession)
                    .where(
                        AuthSession.id == session_id,
                        AuthSession.user_id == user.id,
                        AuthSession.refresh_token_hash == hash_token(raw_refresh_token),
                        AuthSession.revoked_at.is_(None),
                    )
                    .values(revoked_at=datetime.now(timezone.utc))
                )
            elif user.refresh_token_hash and verify_token_hash(raw_refresh_token, user.refresh_token_hash):
                user.refresh_token_hash = None
        else:
            # Bearer-only clients do not have a refresh cookie identifying one
            # session; revoke all sessions rather than leaving refresh access.
            await self.db.execute(
                update(AuthSession)
                .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
                .values(revoked_at=datetime.now(timezone.utc))
            )
            user.refresh_token_hash = None
        await self.db.flush()

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
