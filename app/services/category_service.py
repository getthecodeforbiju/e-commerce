from typing import Optional, List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Category
from app.api.schemas.product import CategoryCreate


class CategoryService:
    """Service for category operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, category_id: UUID) -> Optional[Category]:
        """Get category by ID."""
        result = await self.session.execute(
            select(Category).where(Category.id == category_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Category]:
        """Get category by name."""
        result = await self.session.execute(
            select(Category).where(Category.name == name)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[Category], int]:
        """Get categories with pagination."""

        # Count total
        total = await self.session.scalar(select(func.count(Category.id)))

        # Get paginated results
        result = await self.session.execute(
            select(Category).offset(skip).limit(limit)
        )
        categories = result.scalars().all()

        return categories, total

    async def create(self, category_data: CategoryCreate) -> Category:
        """Create a new category."""

        # Check name exists
        existing = await self.get_by_name(category_data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists"
            )

        category = Category(**category_data.model_dump())

        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)

        return category

    async def update(
        self,
        category_id: UUID,
        category_data: CategoryCreate
    ) -> Category:
        """Update category."""

        category = await self.get_by_id(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

        # Name conflict
        if category_data.name != category.name:
            existing = await self.get_by_name(category_data.name)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category with this name already exists"
                )

        # Apply updates
        for field, value in category_data.model_dump().items():
            setattr(category, field, value)

        await self.session.commit()
        await self.session.refresh(category)

        return category

    async def delete(self, category_id: UUID) -> bool:
        """Delete category if no products are attached."""

        category = await self.get_by_id(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

        # Ensure products relationship is loaded
        await self.session.refresh(category, ["products"])

        if category.products:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete category. It has {len(category.products)} products."
            )

        await self.session.delete(category)
        await self.session.commit()

        return True
