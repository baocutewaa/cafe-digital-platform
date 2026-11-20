from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.schemas.menu import ProductSummaryOut
from app.schemas.promotion import PromotionOut


class StorefrontStats(BaseModel):
    stores_count: int
    categories_count: int
    products_count: int
    active_promotions_count: int


class StorefrontOverviewResponse(BaseModel):
    brand_name: str
    tagline_vi: str
    tagline_en: str
    story_summary_vi: str
    ai_mode: Literal["online", "fast_lookup_only"]
    ai_model: str | None = None
    embedding_model: str | None = None
    phase: str
    stats: StorefrontStats
    signature_products: list[ProductSummaryOut]
    active_promotions: list[PromotionOut]
