from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel, Column, UniqueConstraint
from sqlalchemy import ARRAY, String, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, TIMESTAMP


class UserRole(str, Enum):
    BUYER = "buyer"
    SELLER = "seller"
    ADMIN = "admin"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True)
    )
    email: str = Field(unique=True, index=True, max_length=255)
    full_name: str = Field(max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)
    hashed_password: str = Field(exclude=True)

    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    role: UserRole = Field(default=UserRole.BUYER)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, nullable=False)
    )

    products: list["Product"] = Relationship(back_populates="seller")
    cart_items: list["CartItem"] = Relationship(back_populates="user")
    orders: list["Order"] = Relationship(back_populates="buyer")


class Category(SQLModel, table=True):
    __tablename__ = "categories"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True)
    )
    name: str = Field(unique=True, max_length=100, index=True)
    description: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    products: list["Product"] = Relationship(back_populates="category")


class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True)
    )

    name: str = Field(max_length=225, index=True)
    description: str
    price: float = Field(ge=0)
    stock: int = Field(default=0, ge=0)
    image_urls: list[str] = Field(default=[], sa_column=Column(ARRAY(String)))
    is_active: bool = Field(default=True)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, nullable=False)
    )

    seller_id: UUID = Field(foreign_key="users.id")
    category_id: Optional[UUID] = Field(default=None, foreign_key="categories.id")

    seller: User = Relationship(back_populates="products")
    category: Optional[Category] = Relationship(back_populates="products")
    cart_items: list["CartItem"] = Relationship(back_populates="product")
    order_items: list["OrderItem"] = Relationship(back_populates="product")


class CartItem(SQLModel, table=True):
    __tablename__ = "cart_items"
    
    __table_args__ = (
        UniqueConstraint('user_id', 'product_id', name='unique_user_product_cart'),
        Index('idx_cart_user_id', 'user_id'),  # Performance index
    )

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True)
    )
    quantity: int = Field(ge=1)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    user_id: UUID = Field(foreign_key="users.id")
    product_id: UUID = Field(foreign_key="products.id")

    user: User = Relationship(back_populates="cart_items")
    product: Product = Relationship(back_populates="cart_items")


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Order(SQLModel, table=True):
    __tablename__ = "orders"
    
    __table_args__ = (
        Index('idx_order_buyer_id', 'buyer_id'),
        Index('idx_order_status', 'status'),
        Index('idx_order_created_at', 'created_at'),
    )

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True)
    )

    order_number: str = Field(unique=True, index=True)
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    total_amount: float = Field(ge=0)

    shipping_address: str
    shipping_city: str
    shipping_zip: str
    shipping_phone: str

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, nullable=False)
    )

    buyer_id: UUID = Field(foreign_key="users.id")

    buyer: User = Relationship(back_populates="orders")
    items: list["OrderItem"] = Relationship(back_populates="order")


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True)
    )
    quantity: int = Field(ge=1)
    price_at_purchase: float = Field(ge=0)

    order_id: UUID = Field(foreign_key="orders.id")
    product_id: UUID = Field(foreign_key="products.id")

    order: Order = Relationship(back_populates="items")
    product: Product = Relationship(back_populates="order_items")
    

