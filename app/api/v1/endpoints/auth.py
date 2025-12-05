
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm

from app.api.schemas.user import UserCreate,  UserResponse, TokenResponse
from app.core.security import create_access_token
from app.database.session import get_session
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Register a new user (Buyer, Seller, or Admin)
    """
    service = UserService(session)
    user = await service.create_user(user_data)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session)
):
    service = UserService(session)
    user = await service.authenticate(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post("/register/buyer", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_buyer(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Quick register buyer with auto role = 'buyer'
    """
    user_data = user_data.model_copy(update={"role": "buyer"})
    service = UserService(session)
    return await service.create_user(user_data)


@router.post("/register/seller", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_seller(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Quick register seller with auto role = 'seller'
    """
    user_data = user_data.model_copy(update={"role": "seller"})
    service = UserService(session)
    return await service.create_user(user_data)
