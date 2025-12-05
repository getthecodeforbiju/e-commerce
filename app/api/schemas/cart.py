from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

#Cart Item Schemas
class CartItemBase(BaseModel):
    """Base cart item schema"""
    product_id: UUID
    quantity: int = Field(ge=1, description="Quantity must be at least 1")
    
    
class CartItemCreate(CartItemBase):
    """Schema for adding item to cart"""
    pass

class CartItemUpdate(BaseModel):
    """Schema for updating cart item quantity"""
    quantity: int = Field(ge=1)
    
class ProductInCart(BaseModel):
    """Product details in cart"""
    id: UUID
    name: str
    price: float
    stock: int
    image_urls: list[str]
    
    model_config = ConfigDict(from_attributes=True)
    
    
class CartItemResponse(BaseModel):
    """Cart item with product details"""
    id: UUID
    quantity: int
    product: ProductInCart
    subtotal: float
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
    
class CartResponse(BaseModel):
    """Complete cart with totals"""
    items: list[CartItemResponse]
    total_items: int
    total_price: float
    
    model_config = ConfigDict(from_attributes=True)
    