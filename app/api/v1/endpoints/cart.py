from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.cart import (
    CartItemCreate,
    CartItemUpdate,
    CartItemResponse,
    CartResponse
)
from app.core.security import get_current_buyer
from app.database.models import User, Product
from app.database.session import get_session
from app.services.cart_service import CartService

router = APIRouter(prefix="/cart", tags=["Shopping Cart"])

@router.get("/",response_model=CartResponse)
async def get_cart(
    current_user: User = Depends(get_current_buyer),
    session: AsyncSession = Depends(get_session)
):
    """
    Get current user's shopping cart
    
    Returns all items in cart with others
    """
    service = CartService(session)
    cart_items = await service.get_user_cart(current_user.id)
    
    #Calculate totals
    item_with_subtotal = []
    total_price  = 0.0
    
    for item in cart_items:
        product = await session.get(Product, item.product_id)
        subtotal = product.price * item.quantity
        total_price += subtotal
        
        # Create response with subtotal
        item_response = CartItemResponse(
            id=item.id,
            quantity=item.quantity,
            product=item.product,
            subtotal=subtotal,
            created_at=item.created_at,
            updated_at=item.updated_at
        )
        item_with_subtotal.append(item_response)
        
    return CartResponse(
        items=item_with_subtotal,
        total_items=len(cart_items),
        total_price=total_price
    )
    
@router.post("/", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    cart_data: CartItemCreate,
    current_user: User = Depends(get_current_buyer),
    session: AsyncSession = Depends(get_session)
):
    """
    Add item to cart (buyers only)
    
    If item already in cart, increase quantity
    """
    service = CartService(session)
    cart_item = await service.add_to_cart(cart_data, current_user)
    
    #Calculate subtotal
    product = await session.get(Product, cart_item.product_id)
    subtotal = product.price * cart_item.quantity
    
    return CartItemResponse(
        id=cart_item.id,
        quantity=cart_item.quantity,
        product=cart_item.product,
        subtotal=subtotal,
        created_at=cart_item.created_at,
        updated_at=cart_item.updated_at
    )
    
    
@router.put("/{cart_item_id}", response_model=CartItemResponse)
async def update_cart_item(
    cart_item_id: UUID,
    update_data: CartItemUpdate,
    current_user: User = Depends(get_current_buyer),
    session: AsyncSession = Depends(get_session)
):
    """
    Update cart item quantity
    """
    service = CartService(session)
    cart_item = await service.update_cart_item(
        cart_item_id,
        update_data,
        current_user
    )
    
    #Claculate subtotal
    product = await session.get(Product,cart_item.product_id)
    subtotal = product.price * cart_item.quantity
    
    return CartItemResponse(
        id=cart_item.id,
        quantity=cart_item.quantity,
        product=cart_item.product,
        subtotal=subtotal,
        created_at=cart_item.created_at,
        updated_at=cart_item.updated_at
    )
    
    
@router.delete("/{cart_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_cart(
    cart_item_id: UUID,
    current_user: User = Depends(get_current_buyer),
    session: AsyncSession = Depends(get_session)
):
    """
    Remove item from cart
    """
    service = CartService(session)
    await service.remove_from_cart(cart_item_id, current_user)
    return None


@router.delete("/",status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    current_user: User = Depends(get_current_buyer),
    session: AsyncSession = Depends(get_session)
):
    """
    Clear entire cart
    """
    
    service = CartService(session)
    await service.clear_cart(current_user)
    return None
    
