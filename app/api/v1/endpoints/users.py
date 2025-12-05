from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.user import UserResponse, UserUpdate
from app.core.security import get_current_active_user
from app.database.models import User
from app.database.session import get_session
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """Update current authenticated user"""
    service = UserService(session)
    updated_user = await service.update_current_user(current_user.id, user_update)
    return updated_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """Soft delete current user (deactivate account)"""
    service = UserService(session)
    await service.delete_user(current_user.id)
    return None
