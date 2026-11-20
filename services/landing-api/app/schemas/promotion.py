from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class PromotionProductRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name_vi: str
    name_en: str
    image_url: str


class PromotionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title_vi: str
    title_en: str | None = None
    summary_vi: str
    conditions_vi: str
    promo_code: str | None = None
    discount_type: Literal["percentage", "fixed_amount", "bundle"]
    discount_value: int
    banner_image_url: str | None = None
    start_at: datetime
    end_at: datetime
    products: list[PromotionProductRef]


class PromotionListResponse(BaseModel):
    items: list[PromotionOut]
    total: int
