from datetime import datetime
from typing import Optional
from uuid import UUID
import secrets
from sqlalchemy.orm import selectinload

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Order, OrderItem, OrderStatus, Product, User, CartItem
from app.api.schemas.order import CheckoutRequest, OrderStatusUpdate


class OrderService:
    """Service for order operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _generate_order_number(self) -> str:
        """Generate unique order number"""
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        random_part = secrets.token_hex(4).upper()
        return f"ORD-{timestamp}-{random_part}"

    async def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """Get order by ID"""
        result = await self.session.execute(
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product)
            )
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_user_orders(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[list[Order], int]:
        """Get all orders for a user"""
        # Count total
        count_query = select(func.count(Order.id)).where(Order.buyer_id == user_id)
        total = await self.session.scalar(count_query)

        # Get orders
        query = (
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product)
            )
            .where(Order.buyer_id == user_id)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        orders = result.scalars().all()

        return list(orders), total

    async def get_all_orders(
        self,
        skip: int = 0,
        limit: int = 20,
        status: Optional[OrderStatus] = None
    ) -> tuple[list[Order], int]:
        """Get all orders (admin only)"""
        query = select(Order)

        if status:
            query = query.where(Order.status == status)

        # Count before pagination
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)

        # Apply loading + ordering + pagination to the same query
        query = (
            query
            .options(
                selectinload(Order.items).selectinload(OrderItem.product)
            )
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(query)
        orders = result.scalars().all()

        return list(orders), total

    async def checkout(self, checkout_data: CheckoutRequest, user: User) -> Order:
        """Create order from cart items"""
        # Load user + cart items + product
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.cart_items).selectinload(CartItem.product)
            )
            .where(User.id == user.id)
        )
        user = result.scalar_one()
        
        if not user.cart_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cart is empty"
            )
        
        total_amount = 0
        order_items_data = []
        
        for cart_item in user.cart_items:
            product = cart_item.product
            
            if not product.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product '{product.name}' is no longer available"
                )
            
            if product.stock < cart_item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Not enough stock for '{product.name}'. Only {product.stock} available"
                )
            
            subtotal = product.price * cart_item.quantity
            total_amount += subtotal
            
            order_items_data.append({
                "product_id": product.id,
                "quantity": cart_item.quantity,
                "price_at_purchase": product.price
            })
        
        # Create order
        order = Order(
            order_number=self._generate_order_number(),
            buyer_id=user.id,
            total_amount=total_amount,
            shipping_address=checkout_data.shipping_address,
            shipping_city=checkout_data.shipping_city,
            shipping_zip=checkout_data.shipping_zip,
            shipping_phone=checkout_data.shipping_phone,
            status=OrderStatus.PENDING
        )
        self.session.add(order)
        await self.session.flush()
        
        # Create items + reduce stock
        for item_data in order_items_data:
            product = await self.session.get(Product, item_data["product_id"])
            
            self.session.add(OrderItem(
                order_id=order.id,
                **item_data
            ))
            
            product.stock -= item_data["quantity"]
            product.updated_at = datetime.utcnow()
        
        # Clear cart
        for cart_item in user.cart_items:
            await self.session.delete(cart_item)
        
        await self.session.commit()
        
        # Return full order
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .where(Order.id == order.id)
        )
        return result.scalar_one()

    async def update_status(
        self,
        order_id: UUID,
        status_update: OrderStatusUpdate,
        user: User
    ) -> Order:
        """Update order status (admin or seller)"""
        order = await self.get_by_id(order_id)

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        # Update status
        order.status = status_update.status
        order.updated_at = datetime.utcnow()

        await self.session.commit()
        result = await self.session.execute(
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product)
            )
            .where(Order.id == order.id)
        )
        order = result.scalar_one()
        return order

    async def cancel_order(
        self,
        order_id: UUID,
        user: User
    ) -> Order:
        """
        Cancel order (buyer only, before shipped)
        
        Restores stock
        """
        order = await self.get_by_id(order_id)

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        # Check ownership
        if order.buyer_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not your order"
            )

        # Check if can cancel
        if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel order with status: {order.status}"
            )

        # Restore stock
        for item in order.items:
            product = item.product
            product.stock += item.quantity
            product.updated_at = datetime.utcnow()

        # Cancel order
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(order)

        return order