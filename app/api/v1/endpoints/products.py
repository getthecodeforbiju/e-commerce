from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse
)

from app.core.security import get_current_seller
from app.database.models import User
from app.database.session import get_session
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


# LIST ALL PRODUCTS (PUBLIC)
@router.get("/", response_model=ProductListResponse)
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    category_id: Optional[UUID] = Query(None),
    session: AsyncSession = Depends(get_session)
):
    """List all active products (public endpoint)."""

    service = ProductService(session)

    products, total = await service.get_all(
        skip=skip,
        limit=limit,
        search=search,
        category_id=category_id,
        is_active=True
    )

    return ProductListResponse(total=total, products=products)


# GET SINGLE PRODUCT (PUBLIC)
@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    """Get a single product by ID."""

    service = ProductService(session)
    product = await service.get_by_id(product_id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return product


# GET PRODUCTS OF CURRENT SELLER
@router.get("/seller/my-products", response_model=ProductListResponse)
async def get_my_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_seller: User = Depends(get_current_seller),
    session: AsyncSession = Depends(get_session)
):
    """Get all products of the currently logged-in seller."""

    service = ProductService(session)

    products, total = await service.get_seller_products(
        seller_id=current_seller.id,
        skip=skip,
        limit=limit
    )

    return ProductListResponse(total=total, products=products)


# CREATE PRODUCT (SELLER ONLY)
@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_seller: User = Depends(get_current_seller),
    session: AsyncSession = Depends(get_session)
):
    """Create a new product (only sellers allowed)."""

    service = ProductService(session)
    product = await service.create(product_data, current_seller)

    return product


# UPDATE PRODUCT (SELLER ONLY)
@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    product_update: ProductUpdate,
    current_seller: User = Depends(get_current_seller),
    session: AsyncSession = Depends(get_session)
):
    """Update a product — only the seller who owns it can update."""

    service = ProductService(session)
    product = await service.update(product_id, product_update, current_seller)

    return product


# DELETE PRODUCT (SELLER ONLY)
@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    current_seller: User = Depends(get_current_seller),
    session: AsyncSession = Depends(get_session)
):
    """Soft-delete (deactivate) a product — only the owner can delete."""

    service = ProductService(session)
    await service.delete(product_id, current_seller)

    return None
