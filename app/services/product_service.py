from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Product, Category, User
from app.api.schemas.product import ProductCreate, ProductUpdate
from sqlalchemy.orm import joinedload

class ProductService:
    """Service for product operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, product_id: UUID) -> Optional[Product]:
        q = (
            select(Product)
            .options(joinedload(Product.category), joinedload(Product.seller))
            .where(Product.id == product_id)
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        category_id: Optional[UUID] = None,
        is_active: Optional[bool] = True
    ) -> tuple[list[Product], int]:
        query = select(Product).options(joinedload(Product.category), joinedload(Product.seller))

        if is_active is not None:
            query = query.where(Product.is_active == is_active)

        if category_id:
            query = query.where(Product.category_id == category_id)

        if search:
            search_filter = or_(
                Product.name.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%")
            )
            query = query.where(search_filter)

        query = query.order_by(Product.created_at.desc())

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        products = result.scalars().all()

        return list(products), total


    async def get_seller_products(
        self,
        seller_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[list[Product], int]:
        query = (
            select(Product)
            .options(joinedload(Product.category), joinedload(Product.seller))
            .where(Product.seller_id == seller_id)
            .order_by(Product.created_at.desc())
        )

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        products = result.scalars().all()

        return list(products), total

    

    async def create(self, product_data: ProductCreate, seller: User) -> Product:
        if product_data.category_id:
            category = await self.session.get(Category, product_data.category_id)
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Category not found"
                )

        product = Product(
            **product_data.model_dump(),
            seller_id=seller.id
        )

        self.session.add(product)
        await self.session.commit()
        # refresh to load relationships so serialization won't trigger lazy-load
        await self.session.refresh(product, ["category", "seller"])
        return product


    

    async def update(
        self,
        product_id: UUID,
        product_update: ProductUpdate,
        seller: User
    ) -> Product:
        """Update a product (seller must own it)"""
        product = await self.get_by_id(product_id)

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        if product.seller_id != seller.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own products"
            )

        # Validate category if being updated
        if product_update.category_id:
            category = await self.session.get(Category, product_update.category_id)
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Category not found"
                )

        # Extract only provided fields
        update_data = product_update.model_dump(exclude_unset=True)

        # Prevent seller_id modification
        if "seller_id" in update_data:
            update_data.pop("seller_id")

        # Apply updates
        for field, value in update_data.items():
            setattr(product, field, value)

        product.updated_at = datetime.utcnow()

        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)

        return product

    async def delete(self, product_id: UUID, seller: User) -> bool:
        """Soft delete by deactivating"""
        product = await self.get_by_id(product_id)

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        if product.seller_id != seller.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own products"
            )

        # Soft delete
        product.is_active = False
        product.updated_at = datetime.utcnow()

        self.session.add(product)
        await self.session.commit()

        return True
