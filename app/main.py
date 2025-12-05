from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from app.config import settings
from app.database.session import create_db_tables
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events"""
    # Startup: Create database tables
    await create_db_tables()
    print("✅ Database tables created")
    yield
    # Shutdown
    print("👋 Shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="🛍️ E-commerce API with FastAPI - Authentication, Products, Cart, Orders",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": {
            "swagger": "/docs",
            "scalar": "/scalar",
            "redoc": "/redoc"
        },
        "api": settings.API_V1_PREFIX,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/scalar", include_in_schema=False)
async def scalar_docs():
    """Scalar API Documentation - Modern, beautiful docs"""
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=f"{settings.APP_NAME} API"
    )