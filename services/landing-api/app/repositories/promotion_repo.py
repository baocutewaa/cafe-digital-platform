from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.promotion import Promotion, PromotionProduct


class PromotionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active_promotions(self, now: datetime | None = None) -> list[Promotion]:
        current = now or datetime.now(UTC)
        stmt = (
            select(Promotion)
            .where(
                Promotion.is_active.is_(True),
                Promotion.start_at <= current,
                Promotion.end_at >= current,
            )
            .options(
                selectinload(Promotion.promotion_products).selectinload(
                    PromotionProduct.product
                )
            )
            .order_by(Promotion.start_at.desc(), Promotion.slug)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_active_promotions(self, now: datetime | None = None) -> int:
        current = now or datetime.now(UTC)
        stmt = select(func.count(Promotion.id)).where(
            Promotion.is_active.is_(True),
            Promotion.start_at <= current,
            Promotion.end_at >= current,
        )
        return int((await self.session.execute(stmt)).scalar_one())
