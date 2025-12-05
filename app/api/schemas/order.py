from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.database.models import OrderStatus

# Checkout Schema
class CheckoutRequest(BaseModel):
    """Schema for checkout - creating order fro cart"""
    shipping_address: str = Field(min_length=5)
    shipping_city: str = Field(min_length=2)
    shipping_zip: str = Field(min_length=3)
    shipping_phone: str = Field(min_length=10)
    
    
# Order Item Response
class OrderItemResponse(BaseModel):
    """Order item details"""
    id: UUID
    product_id: UUID
    product_name:str
    quantity: int
    price_at_purchase: float
    subtotal: float
    
    model_config = ConfigDict(from_attributes=True)
    
    
# Order Response
class OrderResponse(BaseModel):
    """Complete oredr details"""
    id: UUID
    order_number: str
    status: OrderStatus
    total_amount: float
    shipping_address: str
    shipping_city: str
    shipping_zip: str
    shipping_phone: str
    items: list[OrderItemResponse]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
    
    # Order List Response
class OrderListResponse(BaseModel):
    """paginated order list"""
    total: int
    orders: list[OrderResponse]
    
    
# Order Status Update (for sellers/admins)
class OrderStatusUpdate(BaseModel):
    """update order status"""
    status: OrderStatus