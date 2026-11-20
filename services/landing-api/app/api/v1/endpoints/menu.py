from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.menu_repo import ProductFilterParams
from app.schemas.menu import (
    CategoryListResponse,
    ProductDetailOut,
    ProductListResponse,
)
from app.services.menu_service import MenuService

router = APIRouter(prefix="/menu", tags=["Menu"])


@router.get("/categories", response_model=CategoryListResponse)
async def list_categories(db: AsyncSession = Depends(get_db)) -> CategoryListResponse:
    """Danh sách danh mục đồ uống và bánh ngọt của BREW & BEAN."""
    service = MenuService(db)
    return await service.list_categories()


@router.get("/products", response_model=ProductListResponse)
async def list_products(
    category: str | None = Query(default=None, description="Lọc theo slug danh mục"),
    max_price: int | None = Query(default=None, ge=0, description="Giá tối đa (VND)"),
    caffeine_level: Literal["none", "low", "medium", "high"] | None = Query(
        default=None, description="Mức caffeine"
    ),
    has_milk: bool | None = Query(default=None, description="Có chứa sữa động vật/kem hay không"),
    taste_tag: str | None = Query(default=None, description="Lọc theo tag hương vị"),
    signature: bool | None = Query(default=None, description="Chỉ lấy món Signature"),
    featured: bool | None = Query(default=None, description="Chỉ lấy món nổi bật"),
    q: str | None = Query(default=None, min_length=1, max_length=100, description="Từ khóa"),
    db: AsyncSession = Depends(get_db),
) -> ProductListResponse:
    """Lọc sản phẩm đa chiều phục vụ Menu UI và Bean AI."""
    service = MenuService(db)
    filters = ProductFilterParams(
        category=category,
        max_price=max_price,
        caffeine_level=caffeine_level,
        has_milk=has_milk,
        taste_tag=taste_tag,
        signature=signature,
        featured=featured,
        q=q,
    )
    return await service.list_products(filters)


@router.get("/products/{slug}", response_model=ProductDetailOut)
async def get_product_detail(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> ProductDetailOut:
    """Chi tiết sản phẩm: variants (size/giá/calo), nguyên liệu và cảnh báo dị ứng."""
    service = MenuService(db)
    return await service.get_product_detail(slug)
