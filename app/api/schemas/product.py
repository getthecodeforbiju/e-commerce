from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict



# Category Schemas

class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)



# Product Schemas

class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    price: float = Field(gt=0, description="Price must be greater than 0")
    stock: int = Field(ge=0, description="Stock cannot be negative")
    category_id: Optional[UUID] = None
    image_urls: list[str] = Field(default_factory=list)


class ProductCreate(ProductBase):
    """Schema for creating a product (sellers only)"""
    pass


class ProductUpdate(BaseModel):
    """Schema for updating a product"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    category_id: Optional[UUID] = None
    image_urls: Optional[list[str]] = None
    is_active: Optional[bool] = None



# Seller Info

class SellerInfo(BaseModel):
    id: UUID
    full_name: str
    email: str

    model_config = ConfigDict(from_attributes=True)



# Product Response

class ProductResponse(ProductBase):
    id: UUID
    is_active: bool
    seller_id: UUID
    seller: SellerInfo
    category: Optional[CategoryResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)



# Paginated List

class ProductListResponse(BaseModel):
    total: int
    products: list[ProductResponse]
    
    
#Schema for paginated category list
class CategoryListResponse(BaseModel):
    total: int
    categories: list[CategoryResponse]
    
    
    