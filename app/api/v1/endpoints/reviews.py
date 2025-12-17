from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.review import (
    ReviewCreate,
    ReviewUpdate,
    ReviewResponse,
    ReviewListResponse,
    ProductRatingSummary
)
from app.core.security import get_current_active_user
from app.database.models import User
from app.database.session import get_session
from app.services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["Reviews & Ratings"])


# PUBLIC ENDPOINTS

@router.get("/products/{product_id}", response_model=ReviewListResponse)
async def get_product_reviews(
    product_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    rating: Optional[int] = Query(None, ge=1, le=5, description="Filter by rating"),
    session: AsyncSession = Depends(get_session)
):
    """
    Get all reviews for a product (public endpoint)
    
    - Filter by rating (optional)
    - Returns rating distribution
    """
    service = ReviewService(session)
    
    reviews, total = await service.get_product_reviews(
        product_id,
        skip=skip,
        limit=limit,
        rating_filter=rating
    )
    
    # Get rating distribution
    distribution = await service.get_rating_distribution(product_id)
    
    # Calculate average
    total_ratings = sum(distribution.values())
    if total_ratings > 0:
        avg_rating = sum(rating * count for rating, count in distribution.items()) / total_ratings
    else:
        avg_rating = None
    
    return ReviewListResponse(
        total=total,
        average_rating=round(avg_rating, 2) if avg_rating else None,
        rating_distribution=distribution,
        reviews=reviews
    )


@router.get("/products/{product_id}/summary", response_model=ProductRatingSummary)
async def get_product_rating_summary(
    product_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    """
    Get rating summary for a product (public endpoint)
    
    Returns:
    - Average rating
    - Total reviews
    - Rating distribution
    """
    service = ReviewService(session)
    
    distribution = await service.get_rating_distribution(product_id)
    
    total_ratings = sum(distribution.values())
    if total_ratings > 0:
        avg_rating = sum(rating * count for rating, count in distribution.items()) / total_ratings
    else:
        avg_rating = None
    
    return ProductRatingSummary(
        product_id=product_id,
        average_rating=round(avg_rating, 2) if avg_rating else None,
        total_reviews=total_ratings,
        rating_distribution=distribution
    )


# ============================================
# AUTHENTICATED ENDPOINTS
# ============================================

@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a review for a product
    
    - Automatically marks as verified if user purchased the product
    - One review per user per product
    """
    service = ReviewService(session)
    return await service.create(review_data, current_user)


@router.get("/my-reviews", response_model=list[ReviewResponse])
async def get_my_reviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """Get all reviews written by current user"""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.database.models import Review
    
    query = (
        select(Review)
        .options(selectinload(Review.user))
        .where(Review.user_id == current_user.id)
        .order_by(Review.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    result = await session.execute(query)
    reviews = result.scalars().all()
    
    return reviews


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    """Get a single review by ID"""
    service = ReviewService(session)
    review = await service.get_by_id(review_id)
    
    if not review:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    return review


@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: UUID,
    review_update: ReviewUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """Update your own review"""
    service = ReviewService(session)
    return await service.update(review_id, review_update, current_user)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete your own review"""
    service = ReviewService(session)
    await service.delete(review_id, current_user)
    return None