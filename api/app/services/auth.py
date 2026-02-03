from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.core.auth import hash_password, verify_password, create_access_token, create_refresh_token, verify_token
from app.schemas.auth import RegisterRequest, LoginRequest


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

        access_token = create_access_token(user.email)
        refresh_token = create_refresh_token(user.email)
        user.refresh_token_hash = hash_password(refresh_token)
        await self.db.flush()
        return access_token, refresh_token, user

    async def refresh(self, raw_refresh_token: str) -> str:
        email = verify_token(raw_refresh_token)
        if not email:
            raise ValueError("Invalid or expired refresh token")

        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        if not user.refresh_token_hash:
            raise ValueError("Refresh token has been revoked")

        if not verify_password(raw_refresh_token, user.refresh_token_hash):
            raise ValueError("Refresh token mismatch")

        new_access_token = create_access_token(user.email)
        new_refresh_token = create_refresh_token(user.email)
        user.refresh_token_hash = hash_password(new_refresh_token)
        await self.db.flush()
        return new_access_token, new_refresh_token

    async def logout(self, email: str) -> None:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.refresh_token_hash = None
            await self.db.flush()

    async def change_password(self, email: str, old_password: str, new_password: str) -> None:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(old_password, user.password_hash):
            raise ValueError("Invalid current password")

        user.password_hash = hash_password(new_password)
        user.refresh_token_hash = None
        await self.db.flush()

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
