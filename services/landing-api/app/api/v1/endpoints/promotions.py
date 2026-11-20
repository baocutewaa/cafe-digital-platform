from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.promotion import PromotionListResponse
from app.services.storefront_service import StorefrontService

router = APIRouter(prefix="/promotions", tags=["Promotions"])


@router.get("/active", response_model=PromotionListResponse)
async def list_active_promotions(
    db: AsyncSession = Depends(get_db),
) -> PromotionListResponse:
    """Danh sách chương trình khuyến mãi đang trong thời hạn hiệu lực."""
    service = StorefrontService(db)
    return await service.list_active_promotions()
