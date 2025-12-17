from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Review, Product, User, Order, OrderItem, OrderStatus
from app.api.schemas.review import ReviewCreate, ReviewUpdate


class ReviewService:
    """Service for review operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_verified_purchase(
        self,
        user_id: UUID,
        product_id: UUID
    ) -> bool:
        """
        Check if user has purchased this product
        """
        query = (
            select(Order)
            .join(OrderItem)
            .where(
                Order.buyer_id == user_id,
                OrderItem.product_id == product_id,
                Order.status.in_([
                    OrderStatus.PAID,
                    OrderStatus.PROCESSING,
                    OrderStatus.SHIPPED,
                    OrderStatus.DELIVERED
                ])
            )
        )
        result = await self.session.execute(query)
        order = result.scalar_one_or_none()
        return order is not None

    async def get_by_id(self, review_id: UUID) -> Optional[Review]:
        """Get review by ID"""
        result = await self.session.execute(
            select(Review)
            .options(selectinload(Review.user))
            .where(Review.id == review_id)
        )
        return result.scalar_one_or_none()

    async def get_user_review_for_product(
        self,
        user_id: UUID,
        product_id: UUID
    ) -> Optional[Review]:
        """Check if user already reviewed this product"""
        result = await self.session.execute(
            select(Review).where(
                Review.user_id == user_id,
                Review.product_id == product_id
            )
        )
        return result.scalar_one_or_none()

    async def get_product_reviews(
        self,
        product_id: UUID,
        skip: int = 0,
        limit: int = 20,
        rating_filter: Optional[int] = None
    ) -> tuple[list[Review], int]:
        """Get all reviews for a product"""
        query = (
            select(Review)
            .options(selectinload(Review.user))
            .where(Review.product_id == product_id)
        )

        if rating_filter:
            query = query.where(Review.rating == rating_filter)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)

        # Get paginated results
        query = (
            query
            .order_by(Review.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(query)
        reviews = result.scalars().all()

        return list(reviews), total

    async def get_rating_distribution(self, product_id: UUID) -> dict[int, int]:
        """Get count of reviews for each rating (1-5)"""
        result = await self.session.execute(
            select(Review.rating, func.count(Review.id))
            .where(Review.product_id == product_id)
            .group_by(Review.rating)
        )
        
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for rating, count in result.all():
            distribution[rating] = count
        
        return distribution

    async def create(
        self,
        review_data: ReviewCreate,
        user: User
    ) -> Review:
        """Create a new review"""
        # Check if product exists
        product = await self.session.get(Product, review_data.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        # Check if user already reviewed this product
        existing_review = await self.get_user_review_for_product(
            user.id,
            review_data.product_id
        )
        if existing_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reviewed this product. Use update instead."
            )

        # Check if verified purchase
        is_verified = await self.check_verified_purchase(
            user.id,
            review_data.product_id
        )

        # Create review
        review = Review(
            **review_data.model_dump(),
            user_id=user.id,
            is_verified_purchase=is_verified
        )

        self.session.add(review)
        await self.session.commit()
        await self.session.refresh(review, ["user"])

        # Update product rating
        await self.update_product_rating(review_data.product_id)

        return review

    async def update(
        self,
        review_id: UUID,
        review_update: ReviewUpdate,
        user: User
    ) -> Review:
        """Update a review"""
        review = await self.get_by_id(review_id)

        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )

        # Check ownership
        if review.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own reviews"
            )

        # Update fields
        update_data = review_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(review, field, value)

        review.updated_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(review)

        # Update product rating
        await self.update_product_rating(review.product_id)

        return review

    async def delete(self, review_id: UUID, user: User) -> bool:
        """Delete a review"""
        review = await self.get_by_id(review_id)

        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )

        # Check ownership
        if review.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own reviews"
            )

        product_id = review.product_id

        await self.session.delete(review)
        await self.session.commit()

        # Update product rating
        await self.update_product_rating(product_id)

        return True

    async def update_product_rating(self, product_id: UUID) -> None:
        """Recalculate and update product's average rating"""
        # Get average rating
        result = await self.session.execute(
            select(
                func.avg(Review.rating),
                func.count(Review.id)
            ).where(Review.product_id == product_id)
        )
        avg_rating, total_reviews = result.one()

        # Update product
        product = await self.session.get(Product, product_id)
        if product:
            product.average_rating = round(avg_rating, 2) if avg_rating else None
            product.total_reviews = total_reviews or 0
            product.updated_at = datetime.utcnow()
            
            await self.session.commit()