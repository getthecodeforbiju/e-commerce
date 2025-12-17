from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# Review Schemas

class ReviewBase(BaseModel):
    """Base review schema"""
    rating: int = Field(ge=1, le=5, description="Rating from 1 to 5 stars")
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = Field(None, max_length=2000)


class ReviewCreate(ReviewBase):
    """Schema for creating a review"""
    product_id: UUID


class ReviewUpdate(BaseModel):
    """Schema for updating a review"""
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = Field(None, max_length=2000)


class ReviewerInfo(BaseModel):
    """User info for review response"""
    id: UUID
    full_name: str
    
    model_config = ConfigDict(from_attributes=True)


class ReviewResponse(ReviewBase):
    """Complete review details"""
    id: UUID
    product_id: UUID
    user_id: UUID
    user: ReviewerInfo
    is_verified_purchase: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ReviewListResponse(BaseModel):
    """Paginated review list"""
    total: int
    average_rating: Optional[float]
    rating_distribution: dict[int, int]  # {5: 10, 4: 5, 3: 2, 2: 1, 1: 0}
    reviews: list[ReviewResponse]


class ProductRatingSummary(BaseModel):
    """Product rating summary"""
    product_id: UUID
    average_rating: Optional[float]
    total_reviews: int
    rating_distribution: dict[int, int]