"""
API для работы с бонусами
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from core.db.session import get_db
from core.db.models import User, BonusTransaction
from core.dependencies import get_current_user
from core.bonus import BonusSystem

router = APIRouter()


# ==================== PYDANTIC SCHEMAS ====================

class BonusInfoResponse(BaseModel):
    """Информация о бонусах пользователя"""
    bonus_balance: int
    total_spent: float
    total_orders: int
    # {"orders": 10, "bonus": 50, "description": "50 ₽ на баланс"}
    next_milestone: dict | None

    class Config:
        from_attributes = True


class BonusTransactionResponse(BaseModel):
    """Транзакция бонусов"""
    id: int
    amount: int
    type: str
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class BonusMilestonesResponse(BaseModel):
    """Информация о порогах начисления бонусов"""
    milestones: dict  # {1: 500, 3: 250, ...}
    bonus_rate: float  # 0.05 = 5%
    max_usage_percent: float  # 0.50 = 50%


# ==================== ENDPOINTS ====================

@router.get("/info", response_model=BonusInfoResponse)
async def get_bonus_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить информацию о бонусах пользователя
    """
    next_milestone = await BonusSystem.get_next_milestone(current_user)

    milestone_dict = None
    if next_milestone:
        milestone_dict = {
            "orders": next_milestone[0],
            "bonus": next_milestone[1],
            "description": next_milestone[2]
        }

    return BonusInfoResponse(
        bonus_balance=current_user.bonus_balance,
        total_spent=float(current_user.total_spent),
        total_orders=current_user.total_orders,
        next_milestone=milestone_dict
    )


@router.get("/transactions", response_model=List[BonusTransactionResponse])
async def get_bonus_transactions(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить историю транзакций бонусов
    """
    result = await db.execute(
        select(BonusTransaction)
        .where(BonusTransaction.user_id == current_user.id)
        .order_by(BonusTransaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    transactions = result.scalars().all()
    return transactions


@router.get("/milestones", response_model=BonusMilestonesResponse)
async def get_bonus_milestones():
    """
    Получить информацию о системе начисления бонусов
    """
    return BonusMilestonesResponse(
        milestones=BonusSystem.BONUS_MILESTONES,
        bonus_rate=BonusSystem.BONUS_RATE,
        max_usage_percent=BonusSystem.MAX_BONUS_USAGE_PERCENT
    )
