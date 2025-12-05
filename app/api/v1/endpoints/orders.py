from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.order import (
    CheckoutRequest,
    OrderResponse,
    OrderListResponse,
    OrderStatusUpdate,
    OrderItemResponse,
)
from app.core.security import get_current_buyer, get_current_admin
from app.database.models import User, OrderStatus
from app.database.session import get_session
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


def build_order_response(order) -> OrderResponse:
    """Convert Order SQLAlchemy model → OrderResponse schema."""

    items_responses = []
    for item in order.items:
        product = item.product  # cache to avoid repeated access

        items_responses.append(
            OrderItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_name=product.name if product else None,
                quantity=item.quantity,
                price_at_purchase=item.price_at_purchase,
                subtotal=item.price_at_purchase * item.quantity,
            )
        )

    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        total_amount=order.total_amount,
        shipping_address=order.shipping_address,
        shipping_city=order.shipping_city,
        shipping_zip=order.shipping_zip,
        shipping_phone=order.shipping_phone,
        items=items_responses,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )



# BUYER ROUTES

@router.post("/checkout", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def checkout(
    checkout_data: CheckoutRequest,
    current_user: User = Depends(get_current_buyer),
    session: AsyncSession = Depends(get_session),
):
    """Checkout — create order from user's cart."""
    service = OrderService(session)
    order = await service.checkout(checkout_data, current_user)
    return build_order_response(order)


@router.get("/my-orders", response_model=OrderListResponse)
async def get_my_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_buyer),
    session: AsyncSession = Depends(get_session),
):
    """Get all orders belonging to the current user."""
    service = OrderService(session)
    orders, total = await service.get_user_orders(
        current_user.id, skip=skip, limit=limit
    )

    return OrderListResponse(
        total=total,
        orders=[build_order_response(order) for order in orders],
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    current_user: User = Depends(get_current_buyer),
    session: AsyncSession = Depends(get_session),
):
    """Get details of a specific order (owner only)."""
    service = OrderService(session)
    order = await service.get_by_id(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your order")

    return build_order_response(order)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: UUID,
    current_user: User = Depends(get_current_buyer),
    session: AsyncSession = Depends(get_session),
):
    """Cancel an order before it is shipped."""
    service = OrderService(session)
    order = await service.cancel_order(order_id, current_user)
    return build_order_response(order)


#                     ADMIN ROUTES

@router.get("/admin/all", response_model=OrderListResponse)
async def get_all_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[OrderStatus] = Query(None),
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    """Get all orders (admin only), optionally filter by status."""
    service = OrderService(session)
    orders, total = await service.get_all_orders(
        skip=skip, limit=limit, status=status
    )

    return OrderListResponse(
        total=total,
        orders=[build_order_response(order) for order in orders],
    )


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: UUID,
    status_update: OrderStatusUpdate,
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    """Update an order's status (admin only)."""
    service = OrderService(session)
    order = await service.update_status(order_id, status_update, current_admin)
    return build_order_response(order)
