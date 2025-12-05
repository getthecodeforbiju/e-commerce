from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select, func, text, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_admin
from app.database.models import User
from app.database.session import get_session

router = APIRouter(prefix="/admin", tags=["Admin"])


# COUNT USERS

@router.get("/users/count")
async def count_users(
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(func.count(User.id)))
    count = result.scalar()
    return {"total_users": count}


# LIST USERS

@router.get("/users/list")
async def list_all_users(
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(User))
    users = result.scalars().all()

    return {
        "total": len(users),
        "users": [
            {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat()
            }
            for user in users
        ]
    }


# FIND DUPLICATE EMAILS

@router.get("/users/duplicates")
async def find_duplicates(
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    query = text("""
        SELECT email, COUNT(*) AS count
        FROM users
        GROUP BY email
        HAVING COUNT(*) > 1
    """)
    result = await session.execute(query)
    duplicates = result.fetchall()

    return {
        "duplicates": [
            {"email": row.email, "count": row.count}
            for row in duplicates
        ]
    }


# REMOVE DUPLICATES KEEPING NEWEST

@router.delete("/users/duplicates", status_code=status.HTTP_204_NO_CONTENT)
async def remove_duplicates(
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    # Get all duplicates with newest id
    query = text("""
        WITH ranked AS (
            SELECT 
                id, email,
                ROW_NUMBER() OVER (PARTITION BY email ORDER BY created_at DESC) AS rn
            FROM users
        )
        DELETE FROM users 
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
    """)

    await session.execute(query)
    await session.commit()
    return None


# DELETE ALL USERS (SAFE)

@router.delete("/users/all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_users(
    confirm: str,
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    if confirm != "DELETE_ALL":
        raise HTTPException(
            status_code=400,
            detail="Must pass confirm=DELETE_ALL"
        )

    # Avoid deleting the current admin
    await session.execute(
        delete(User).where(User.id != current_admin.id)
    )
    await session.commit()

    return None
