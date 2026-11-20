from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.storefront import StorefrontOverviewResponse
from app.services.storefront_service import StorefrontService

router = APIRouter(tags=["Storefront"])


@router.get("/storefront", response_model=StorefrontOverviewResponse)
async def get_storefront_overview(
    db: AsyncSession = Depends(get_db),
) -> StorefrontOverviewResponse:
    """Thông tin tổng quan thương hiệu BREW & BEAN, số liệu nổi bật và trạng thái Bean AI."""
    service = StorefrontService(db)
    return await service.get_overview()
