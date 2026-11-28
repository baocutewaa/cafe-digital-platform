from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.integrations.ollama_client import ollama_client
from app.models.promotion import Promotion
from app.models.store import Store, StoreHour
from app.repositories.menu_repo import MenuRepository, ProductFilterParams
from app.repositories.promotion_repo import PromotionRepository
from app.repositories.store_repo import StoreRepository
from app.schemas.promotion import PromotionListResponse, PromotionOut, PromotionProductRef
from app.schemas.store import StoreHourOut, StoreListResponse, StoreOut
from app.schemas.storefront import StorefrontOverviewResponse, StorefrontStats
from app.services.menu_service import build_product_summary

VIETNAM_TZ = timezone(timedelta(hours=7))


def compute_store_open_status(
    hours: list[StoreHour],
    now: datetime | None = None,
) -> tuple[bool, StoreHourOut | None]:
    current = (now or datetime.now(VIETNAM_TZ)).astimezone(VIETNAM_TZ)
    weekday = current.weekday()
    current_time = current.time()

    today_hour = next((h for h in hours if h.day_of_week == weekday), None)
    if today_hour is None:
        return False, None

    today_out = StoreHourOut.model_validate(today_hour)
    if today_hour.is_closed:
        return False, today_out

    if today_hour.open_time <= today_hour.close_time:
        is_open = today_hour.open_time <= current_time < today_hour.close_time
    else:
        is_open = current_time >= today_hour.open_time or current_time < today_hour.close_time
    return is_open, today_out


def build_store_out(store: Store, now: datetime | None = None) -> StoreOut:
    is_open, today_hours = compute_store_open_status(store.hours, now=now)
    return StoreOut(
        id=store.id,
        slug=store.slug,
        name=store.name,
        address=store.address,
        district=store.district,
        city=store.city,
        phone=store.phone,
        google_maps_url=store.google_maps_url,
        latitude=store.latitude,
        longitude=store.longitude,
        amenities=list(store.amenities or []),
        image_url=store.image_url,
        is_active=store.is_active,
        is_open_now=is_open,
        today_hours=today_hours,
        hours=[StoreHourOut.model_validate(h) for h in store.hours],
    )


def build_promotion_out(promo: Promotion) -> PromotionOut:
    products = [
        PromotionProductRef.model_validate(pp.product)
        for pp in promo.promotion_products
        if pp.product and pp.product.is_active
    ]
    products.sort(key=lambda item: item.name_vi)
    return PromotionOut(
        id=promo.id,
        slug=promo.slug,
        title_vi=promo.title_vi,
        title_en=promo.title_en,
        summary_vi=promo.summary_vi,
        conditions_vi=promo.conditions_vi,
        promo_code=promo.promo_code,
        discount_type=promo.discount_type,  # type: ignore[arg-type]
        discount_value=promo.discount_value,
        banner_image_url=promo.banner_image_url,
        start_at=promo.start_at,
        end_at=promo.end_at,
        products=products,
    )


class StorefrontService:
    def __init__(self, session: AsyncSession) -> None:
        self.store_repo = StoreRepository(session)
        self.menu_repo = MenuRepository(session)
        self.promo_repo = PromotionRepository(session)

    async def get_overview(self) -> StorefrontOverviewResponse:
        # Note: Sequential DB queries on one AsyncSession (asyncpg does not allow
        # concurrent operations on the same connection), paired concurrently with
        # cached Ollama health check.
        ollama_task = asyncio.create_task(ollama_client.check_health(use_cache=True))
        stores_count = await self.store_repo.count_active_stores()
        categories_count = await self.menu_repo.count_active_categories()
        products_count = await self.menu_repo.count_active_products()
        signature_products = await self.menu_repo.list_products(
            ProductFilterParams(signature=True)
        )
        active_promos = await self.promo_repo.list_active_promotions()
        ollama_health = await ollama_task

        return StorefrontOverviewResponse(
            brand_name="BREW & BEAN",
            tagline_vi="Nghệ thuật Cà phê Đặc sản & Trợ lý Barista AI",
            tagline_en="Specialty Coffee Craft & Personal AI Barista",
            story_summary_vi=(
                "Hệ thống không gian cà phê đặc sản quanh vành đai Hồ Tây, Hà Nội — "
                "kết nối hạt Arabica Cầu Đất 1.650m và Robusta Buôn Ma Thuột rang vừa "
                "với đúng khẩu vị của bạn."
            ),
            ai_mode=ollama_health.get("ai_mode", "fast_lookup_only"),
            ai_model=ollama_health.get("llm_model"),
            embedding_model=ollama_health.get("embedding_model"),
            phase="P1 — Storefront Catalog, Seed Data & Read API",
            stats=StorefrontStats(
                stores_count=stores_count,
                categories_count=categories_count,
                products_count=products_count,
                active_promotions_count=len(active_promos),
            ),
            signature_products=[build_product_summary(p) for p in signature_products],
            active_promotions=[build_promotion_out(p) for p in active_promos],
        )

    async def list_stores(self) -> StoreListResponse:
        stores = await self.store_repo.list_active_stores()
        items = [build_store_out(s) for s in stores]
        return StoreListResponse(items=items, total=len(items))

    async def get_store_detail(self, slug: str) -> StoreOut:
        store = await self.store_repo.get_by_slug(slug)
        if store is None:
            raise ResourceNotFoundError(f"Không tìm thấy chi nhánh '{slug}'.")
        return build_store_out(store)

    async def list_active_promotions(self) -> PromotionListResponse:
        promos = await self.promo_repo.list_active_promotions()
        items = [build_promotion_out(p) for p in promos]
        return PromotionListResponse(items=items, total=len(items))
