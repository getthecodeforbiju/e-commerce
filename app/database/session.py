from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)


async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def create_db_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        

async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session