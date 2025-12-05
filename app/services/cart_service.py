from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CartItem, Product, User
from app.api.schemas.cart import CartItemCreate, CartItemUpdate


class CartService:
    """Service for shopping cart operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # GET USER CART
    async def get_user_cart(self, user_id: UUID) -> list[CartItem]:
        result = await self.session.execute(
            select(CartItem).where(CartItem.user_id == user_id)
        )
        return list(result.scalars().all())

    # GET ONE CART ITEM
    async def get_cart_item(
        self,
        user_id: UUID,
        product_id: UUID,
    ) -> Optional[CartItem]:
        result = await self.session.execute(
            select(CartItem).where(
                CartItem.user_id == user_id,
                CartItem.product_id == product_id
            )
        )
        return result.scalar_one_or_none()

    # ADD / UPDATE CART ITEM
    async def add_to_cart(
        self,
        cart_data: CartItemCreate,
        user: User
    ) -> CartItem:

        # Ensure product exists
        product = await self.session.get(Product, cart_data.product_id)

        if not product or not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product is not available"
            )

        # Stock check
        if product.stock < cart_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only {product.stock} items available in stock"
            )

        # Check if already exists
        existing_item = await self.get_cart_item(user.id, cart_data.product_id)

        if existing_item:
            new_quantity = existing_item.quantity + cart_data.quantity

            if new_quantity > product.stock:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot add more. Only {product.stock} items available"
                )

            existing_item.quantity = new_quantity
            await self.session.commit()
            await self.session.refresh(existing_item)
            return existing_item

        # Create fresh cart item
        cart_item = CartItem(
            user_id=user.id,
            product_id=cart_data.product_id,
            quantity=cart_data.quantity
        )

        self.session.add(cart_item)
        await self.session.commit()
        await self.session.refresh(cart_item)
        return cart_item

    # UPDATE CART ITEM QUANTITY
    async def update_cart_item(
        self,
        cart_item_id: UUID,
        update_data: CartItemUpdate,
        user: User
    ) -> CartItem:

        cart_item = await self.session.get(CartItem, cart_item_id)

        if not cart_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart item not found"
            )

        # Ownership check
        if cart_item.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not your cart item"
            )

        # Load product safely (NO lazy loading)
        product = await self.session.get(Product, cart_item.product_id)

        if update_data.quantity > product.stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only {product.stock} items available"
            )

        cart_item.quantity = update_data.quantity
        await self.session.commit()
        await self.session.refresh(cart_item)
        return cart_item

    # REMOVE CART ITEM
    async def remove_from_cart(
        self,
        cart_item_id: UUID,
        user: User
    ) -> bool:

        cart_item = await self.session.get(CartItem, cart_item_id)

        if not cart_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart item not found"
            )

        if cart_item.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not your cart item"
            )

        await self.session.delete(cart_item)
        await self.session.commit()
        return True

    # CLEAR CART
    async def clear_cart(self, user: User) -> bool:
        cart_items = await self.get_user_cart(user.id)

        for item in cart_items:
            await self.session.delete(item)

        await self.session.commit()
        return True
