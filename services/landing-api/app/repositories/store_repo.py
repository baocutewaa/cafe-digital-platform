from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.store import Store


class StoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active_stores(self) -> list[Store]:
        stmt = (
            select(Store)
            .where(Store.is_active.is_(True))
            .options(selectinload(Store.hours))
            .order_by(Store.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_slug(self, slug: str) -> Store | None:
        stmt = (
            select(Store)
            .where(Store.slug == slug, Store.is_active.is_(True))
            .options(selectinload(Store.hours))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_active_stores(self) -> int:
        stmt = select(func.count(Store.id)).where(Store.is_active.is_(True))
        result = await self.session.execute(stmt)
        return int(result.scalar_one())
