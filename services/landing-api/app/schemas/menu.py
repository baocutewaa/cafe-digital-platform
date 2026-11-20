from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CategorySummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name_vi: str
    name_en: str


class CategoryOut(CategorySummaryOut):
    description_vi: str | None = None
    description_en: str | None = None
    display_order: int
    product_count: int = 0


class CategoryListResponse(BaseModel):
    items: list[CategoryOut]
    total: int


class ProductVariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    size: Literal["small", "regular", "large"]
    temperature: Literal["hot", "iced", "both"]
    price_vnd: int
    calories_kcal: int | None = None
    is_available: bool


class ProductIngredientOut(BaseModel):
    code: str
    name_vi: str
    name_en: str
    allergen_code: str | None = None
    is_optional: bool = False


class ProductSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name_vi: str
    name_en: str
    short_description_vi: str
    short_description_en: str | None = None
    image_url: str
    category: CategorySummaryOut
    taste_tags: list[str]
    caffeine_level: Literal["none", "low", "medium", "high"]
    bitterness_level: int
    sweetness_level: int
    has_milk: bool
    is_signature: bool
    is_featured: bool
    min_price_vnd: int
    max_price_vnd: int
    allergens: list[str]
    variants: list[ProductVariantOut]


class ProductDetailOut(ProductSummaryOut):
    story_vi: str | None = None
    ingredients: list[ProductIngredientOut]


class ProductListResponse(BaseModel):
    items: list[ProductSummaryOut]
    total: int
