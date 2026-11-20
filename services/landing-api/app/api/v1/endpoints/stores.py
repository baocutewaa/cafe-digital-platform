from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.store import StoreListResponse, StoreOut
from app.services.storefront_service import StorefrontService

router = APIRouter(prefix="/stores", tags=["Stores"])


@router.get("", response_model=StoreListResponse)
async def list_stores(db: AsyncSession = Depends(get_db)) -> StoreListResponse:
    """Danh sách chi nhánh BREW & BEAN kèm giờ mở cửa và trạng thái đang mở/đóng."""
    service = StorefrontService(db)
    return await service.list_stores()


@router.get("/{slug}", response_model=StoreOut)
async def get_store_detail(slug: str, db: AsyncSession = Depends(get_db)) -> StoreOut:
    """Chi tiết một chi nhánh theo slug."""
    service = StorefrontService(db)
    return await service.get_store_detail(slug)
