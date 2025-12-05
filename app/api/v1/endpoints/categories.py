from uuid import UUID

from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.product import CategoryCreate, CategoryResponse,CategoryListResponse
from app.core.security import get_current_admin
from app.database.models import User
from app.database.session import get_session
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("/", response_model=CategoryListResponse)
async def list_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_session)
):
    """
    List all categories (public endpoint)
    """
    service = CategoryService(session)
    categories, total = await service.get_all(skip=skip, limit=limit)

    return CategoryListResponse(
        total=total,
        categories=categories
    )


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    """Get a single category by ID"""
    service = CategoryService(session)
    category = await service.get_by_id(category_id)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Create a new category (admin only)"""
    service = CategoryService(session)
    return await service.create(category_data)


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    category_data: CategoryCreate,
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Update a category (admin only)"""
    service = CategoryService(session)
    return await service.update(category_id, category_data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Delete a category (admin only).
    Cannot delete if category has products.
    """
    service = CategoryService(session)
    await service.delete(category_id)
    return None
