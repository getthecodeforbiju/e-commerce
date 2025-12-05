from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.security import get_password_hash, verify_password
from app.database.models import User
from app.api.schemas.user import UserCreate, UserUpdate


class UserService:
    """Service for user operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    #Get user by email
    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    # Get user by ID
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    # Create new user
    async def create_user(self, user_data: UserCreate) -> User:
        existing_user = await self.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            phone=user_data.phone,
            role=user_data.role,
            hashed_password=get_password_hash(user_data.password),
        )

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        return user

    # Authentication
    async def authenticate(self, email: str, password: str) -> Optional[User]:
        user = await self.get_by_email(email)
        if not user:
            return None
        
        if not user.is_active:  # prevent deleted users from logging in
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        return user

    # Update user
    async def update_user(self, user_id: UUID, user_update: UserUpdate) -> User:
        user = await self.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        update_data = user_update.model_dump(exclude_unset=True)

        # Apply updates
        for field, value in update_data.items():
            setattr(user, field, value)

        # update timestamp
        user.updated_at = datetime.utcnow()

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        return user

    # Soft delete user
    async def delete_user(self, user_id: UUID) -> None:
        user = await self.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user.is_active = False
        user.updated_at = datetime.utcnow()

        self.session.add(user)
        await self.session.commit()
