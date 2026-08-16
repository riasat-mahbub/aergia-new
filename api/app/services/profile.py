"""Persistence service for the authenticated user's singleton profile."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.profile import UserProfile, UserProfileUpdate


class ProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_profile(self, user: User) -> UserProfile:
        profile = UserProfile.model_validate(user.profile_data)
        if not profile.email or not profile.email.strip():
            profile.email = user.email
        return profile

    async def update_profile(self, user: User, data: UserProfileUpdate) -> UserProfile:
        user.profile_data = data.model_dump()
        await self.db.flush()
        return await self.get_profile(user)
