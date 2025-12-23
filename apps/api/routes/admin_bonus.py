"""
Административные эндпоинты для управления бонусами
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from core.db.session import get_db
from core.db.models import User, BonusTransaction
from core.dependencies import get_admin_user

router = APIRouter()


# ==================== PYDANTIC SCHEMAS ====================

class UserBonusInfo(BaseModel):
    """Информация о бонусах пользователя"""
    user_id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    bonus_balance: int
    total_spent: float
    total_orders: int

    class Config:
        from_attributes = True


class AdminBonusActionRequest(BaseModel):
    """Запрос на изменение бонусов"""
    user_id: int
    amount: int  # Положительное = начисление, отрицательное = списание
    description: str


class SetBonusBalanceRequest(BaseModel):
    """Установить точный баланс бонусов"""
    user_id: int
    new_balance: int
    description: str = "Установка баланса администратором"


class BonusTransactionResponse(BaseModel):
    """Транзакция бонусов с информацией о пользователе"""
    id: int
    user_id: int
    username: str | None
    first_name: str | None
    amount: int
    type: str
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== ENDPOINTS ====================

@router.get("/users", response_model=List[UserBonusInfo])
async def get_users_bonuses(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    Получить список пользователей с информацией о бонусах
    """
    result = await db.execute(
        select(User)
        .order_by(User.bonus_balance.desc())
        .limit(limit)
        .offset(offset)
    )
    users = result.scalars().all()
    
    return [
        UserBonusInfo(
            user_id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            first_name=user.first_name,
            bonus_balance=user.bonus_balance,
            total_spent=float(user.total_spent),
            total_orders=user.total_orders
        )
        for user in users
    ]


@router.get("/users/{user_id}", response_model=UserBonusInfo)
async def get_user_bonuses(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    Получить информацию о бонусах конкретного пользователя
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserBonusInfo(
        user_id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        bonus_balance=user.bonus_balance,
        total_spent=float(user.total_spent),
        total_orders=user.total_orders
    )


@router.post("/add")
async def add_bonuses(
    request: AdminBonusActionRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    Начислить бонусы пользователю
    """
    if request.amount <= 0:
        raise HTTPException(
            status_code=400, 
            detail="Amount must be positive for adding bonuses"
        )
    
    # Найти пользователя
    result = await db.execute(
        select(User).where(User.id == request.user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Начислить бонусы
    user.bonus_balance += request.amount
    
    # Создать транзакцию
    transaction = BonusTransaction(
        user_id=user.id,
        amount=request.amount,
        type="bonus_gift",
        description=f"Начисление администратором: {request.description}"
    )
    db.add(transaction)
    
    await db.commit()
    await db.refresh(user)
    
    return {
        "ok": True,
        "message": f"Added {request.amount} bonuses to user {user.id}",
        "new_balance": user.bonus_balance
    }


@router.post("/subtract")
async def subtract_bonuses(
    request: AdminBonusActionRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    Списать бонусы у пользователя
    """
    if request.amount <= 0:
        raise HTTPException(
            status_code=400, 
            detail="Amount must be positive for subtracting bonuses"
        )
    
    # Найти пользователя
    result = await db.execute(
        select(User).where(User.id == request.user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Проверить достаточность бонусов
    if user.bonus_balance < request.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient bonuses. User has {user.bonus_balance}, trying to subtract {request.amount}"
        )
    
    # Списать бонусы
    user.bonus_balance -= request.amount
    
    # Создать транзакцию
    transaction = BonusTransaction(
        user_id=user.id,
        amount=-request.amount,
        type="admin_deduct",
        description=f"Списание администратором: {request.description}"
    )
    db.add(transaction)
    
    await db.commit()
    await db.refresh(user)
    
    return {
        "ok": True,
        "message": f"Subtracted {request.amount} bonuses from user {user.id}",
        "new_balance": user.bonus_balance
    }


@router.post("/set-balance")
async def set_bonus_balance(
    request: SetBonusBalanceRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    Установить точный баланс бонусов пользователю
    """
    if request.new_balance < 0:
        raise HTTPException(
            status_code=400, 
            detail="Balance cannot be negative"
        )
    
    # Найти пользователя
    result = await db.execute(
        select(User).where(User.id == request.user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_balance = user.bonus_balance
    difference = request.new_balance - old_balance
    
    # Установить новый баланс
    user.bonus_balance = request.new_balance
    
    # Создать транзакцию
    transaction = BonusTransaction(
        user_id=user.id,
        amount=difference,
        type="admin_adjust",
        description=f"{request.description} (было: {old_balance}, стало: {request.new_balance})"
    )
    db.add(transaction)
    
    await db.commit()
    await db.refresh(user)
    
    return {
        "ok": True,
        "message": f"Set balance to {request.new_balance} for user {user.id}",
        "old_balance": old_balance,
        "new_balance": user.bonus_balance,
        "difference": difference
    }


@router.get("/transactions", response_model=List[BonusTransactionResponse])
async def get_all_bonus_transactions(
    limit: int = 100,
    offset: int = 0,
    user_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    Получить историю всех транзакций бонусов
    
    Можно фильтровать по user_id
    """
    from sqlalchemy.orm import selectinload
    
    query = select(BonusTransaction).options(selectinload(BonusTransaction.user))
    
    if user_id is not None:
        query = query.where(BonusTransaction.user_id == user_id)
    
    query = query.order_by(BonusTransaction.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    transactions = result.scalars().all()
    
    return [
        BonusTransactionResponse(
            id=t.id,
            user_id=t.user_id,
            username=t.user.username if t.user else None,
            first_name=t.user.first_name if t.user else None,
            amount=t.amount,
            type=t.type,
            description=t.description,
            created_at=t.created_at
        )
        for t in transactions
    ]


@router.get("/statistics")
async def get_bonus_statistics(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    Получить статистику по бонусной системе
    """
    from sqlalchemy import func
    
    # Общая статистика пользователей
    result = await db.execute(
        select(
            func.count(User.id).label("total_users"),
            func.sum(User.bonus_balance).label("total_bonuses"),
            func.avg(User.bonus_balance).label("avg_bonuses"),
            func.max(User.bonus_balance).label("max_bonuses")
        )
    )
    stats = result.one()
    
    # Статистика транзакций
    result = await db.execute(
        select(
            BonusTransaction.type,
            func.count(BonusTransaction.id).label("count"),
            func.sum(BonusTransaction.amount).label("total_amount")
        )
        .group_by(BonusTransaction.type)
    )
    transactions_by_type = result.all()
    
    # Топ пользователей по бонусам
    result = await db.execute(
        select(User)
        .order_by(User.bonus_balance.desc())
        .limit(10)
    )
    top_users = result.scalars().all()
    
    return {
        "total_users": stats.total_users or 0,
        "total_bonuses_in_system": int(stats.total_bonuses or 0),
        "average_bonus_balance": float(stats.avg_bonuses or 0),
        "max_bonus_balance": int(stats.max_bonuses or 0),
        "transactions_by_type": [
            {
                "type": t.type,
                "count": t.count,
                "total_amount": int(t.total_amount)
            }
            for t in transactions_by_type
        ],
        "top_users": [
            {
                "user_id": user.id,
                "telegram_id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "bonus_balance": user.bonus_balance,
                "total_orders": user.total_orders
            }
            for user in top_users
        ]
    }
