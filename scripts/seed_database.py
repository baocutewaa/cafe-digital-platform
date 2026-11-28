#!/usr/bin/env python3
"""
BREW & BEAN — Idempotent Seed Database CLI (Giai đoạn P1)
Validate data/seed/*.json bằng Pydantic và thực hiện UPSERT vào PostgreSQL
theo MIGRATION_DATABASE_URL.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

REPO_ROOT = Path(__file__).resolve().parents[1]
LANDING_API_DIR = REPO_ROOT / "services" / "landing-api"
if str(LANDING_API_DIR) not in sys.path:
    sys.path.insert(0, str(LANDING_API_DIR))

from app.core.config import settings
from app.models.menu import (
    Ingredient,
    MenuCategory,
    Product,
    ProductIngredient,
    ProductVariant,
)
from app.models.promotion import Promotion, PromotionProduct
from app.models.store import Store, StoreHour


class StoreHourSeed(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    open_time: time
    close_time: time
    is_closed: bool = False


class StoreSeed(BaseModel):
    slug: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=150)
    address: str = Field(min_length=1)
    district: str | None = Field(default=None, max_length=100)
    city: str = Field(default="Hà Nội", max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    google_maps_url: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    amenities: list[str] = Field(default_factory=list)
    image_url: str | None = None
    is_active: bool = True
    hours: list[StoreHourSeed] = Field(min_length=1, max_length=7)


class CategorySeed(BaseModel):
    slug: str = Field(min_length=1, max_length=100)
    name_vi: str = Field(min_length=1, max_length=120)
    name_en: str = Field(min_length=1, max_length=120)
    description_vi: str | None = None
    description_en: str | None = None
    display_order: int = 0
    is_active: bool = True


class IngredientSeed(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    name_vi: str = Field(min_length=1, max_length=120)
    name_en: str = Field(min_length=1, max_length=120)
    allergen_code: str | None = Field(default=None, max_length=50)


class VariantSeed(BaseModel):
    sku: str = Field(min_length=1, max_length=60)
    size: Literal["small", "regular", "large"]
    temperature: Literal["hot", "iced", "both"] = "both"
    price_vnd: int = Field(ge=0)
    calories_kcal: int | None = Field(default=None, ge=0)
    is_available: bool = True


class ProductIngredientSeed(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    is_optional: bool = False


class ProductSeed(BaseModel):
    slug: str = Field(min_length=1, max_length=120)
    category_slug: str = Field(min_length=1, max_length=100)
    name_vi: str = Field(min_length=1, max_length=150)
    name_en: str = Field(min_length=1, max_length=150)
    short_description_vi: str = Field(min_length=1)
    short_description_en: str | None = None
    story_vi: str | None = None
    image_url: str = Field(min_length=1)
    taste_tags: list[str] = Field(default_factory=list)
    caffeine_level: Literal["none", "low", "medium", "high"] = "medium"
    bitterness_level: int = Field(default=3, ge=1, le=5)
    sweetness_level: int = Field(default=3, ge=1, le=5)
    has_milk: bool = False
    is_signature: bool = False
    is_featured: bool = False
    is_active: bool = True
    display_order: int = 0
    variants: list[VariantSeed] = Field(min_length=1)
    ingredients: list[ProductIngredientSeed] = Field(default_factory=list)


class PromotionSeed(BaseModel):
    slug: str = Field(min_length=1, max_length=120)
    title_vi: str = Field(min_length=1, max_length=200)
    title_en: str | None = Field(default=None, max_length=200)
    summary_vi: str = Field(min_length=1)
    conditions_vi: str = Field(min_length=1)
    promo_code: str | None = Field(default=None, max_length=50)
    discount_type: Literal["percentage", "fixed_amount", "bundle"]
    discount_value: int = Field(ge=0)
    banner_image_url: str | None = None
    start_at: datetime
    end_at: datetime
    is_active: bool = True
    product_slugs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self) -> PromotionSeed:
        if self.end_at <= self.start_at:
            raise ValueError(f"Promotion '{self.slug}': end_at must be after start_at")
        return self


class SeedBundle(BaseModel):
    stores: list[StoreSeed]
    categories: list[CategorySeed]
    ingredients: list[IngredientSeed]
    products: list[ProductSeed]
    promotions: list[PromotionSeed]

    @model_validator(mode="after")
    def validate_references(self) -> SeedBundle:
        category_slugs = {c.slug for c in self.categories}
        ingredient_codes = {i.code for i in self.ingredients}
        product_slugs = {p.slug for p in self.products}
        seen_skus: set[str] = set()

        for product in self.products:
            if product.category_slug not in category_slugs:
                raise ValueError(
                    f"Product '{product.slug}' references unknown category "
                    f"'{product.category_slug}'"
                )
            seen_sizes: set[str] = set()
            for variant in product.variants:
                if variant.sku in seen_skus:
                    raise ValueError(f"Duplicate SKU '{variant.sku}'")
                seen_skus.add(variant.sku)
                if variant.size in seen_sizes:
                    raise ValueError(
                        f"Duplicate size '{variant.size}' in product '{product.slug}'"
                    )
                seen_sizes.add(variant.size)
            for ing in product.ingredients:
                if ing.code not in ingredient_codes:
                    raise ValueError(
                        f"Product '{product.slug}' references unknown ingredient '{ing.code}'"
                    )

        for promo in self.promotions:
            for p_slug in promo.product_slugs:
                if p_slug not in product_slugs:
                    raise ValueError(
                        f"Promotion '{promo.slug}' references unknown product '{p_slug}'"
                    )
        return self


def load_seed_bundle(seed_dir: Path) -> SeedBundle:
    def read_json(filename: str) -> list[dict]:
        path = seed_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing seed file: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    return SeedBundle(
        stores=[StoreSeed.model_validate(item) for item in read_json("stores.json")],
        categories=[CategorySeed.model_validate(item) for item in read_json("categories.json")],
        ingredients=[IngredientSeed.model_validate(item) for item in read_json("ingredients.json")],
        products=[ProductSeed.model_validate(item) for item in read_json("products.json")],
        promotions=[PromotionSeed.model_validate(item) for item in read_json("promotions.json")],
    )


async def upsert_bundle(session: AsyncSession, bundle: SeedBundle) -> dict[str, int]:
    # 1. Stores & StoreHours
    store_ids_by_slug: dict[str, object] = {}
    for s in bundle.stores:
        stmt = (
            insert(Store)
            .values(
                slug=s.slug,
                name=s.name,
                address=s.address,
                district=s.district,
                city=s.city,
                phone=s.phone,
                google_maps_url=s.google_maps_url,
                latitude=s.latitude,
                longitude=s.longitude,
                amenities=s.amenities,
                image_url=s.image_url,
                is_active=s.is_active,
            )
            .on_conflict_do_update(
                index_elements=[Store.slug],
                set_={
                    "name": s.name,
                    "address": s.address,
                    "district": s.district,
                    "city": s.city,
                    "phone": s.phone,
                    "google_maps_url": s.google_maps_url,
                    "latitude": s.latitude,
                    "longitude": s.longitude,
                    "amenities": s.amenities,
                    "image_url": s.image_url,
                    "is_active": s.is_active,
                },
            )
            .returning(Store.id)
        )
        store_id = (await session.execute(stmt)).scalar_one()
        store_ids_by_slug[s.slug] = store_id

        valid_days = [h.day_of_week for h in s.hours]
        await session.execute(
            delete(StoreHour).where(
                StoreHour.store_id == store_id,
                StoreHour.day_of_week.not_in(valid_days),
            )
        )
        for h in s.hours:
            hour_stmt = (
                insert(StoreHour)
                .values(
                    store_id=store_id,
                    day_of_week=h.day_of_week,
                    open_time=h.open_time,
                    close_time=h.close_time,
                    is_closed=h.is_closed,
                )
                .on_conflict_do_update(
                    constraint="uq_store_hours_store_day",
                    set_={
                        "open_time": h.open_time,
                        "close_time": h.close_time,
                        "is_closed": h.is_closed,
                    },
                )
            )
            await session.execute(hour_stmt)

    desired_store_slugs = [s.slug for s in bundle.stores]
    if desired_store_slugs:
        await session.execute(
            update(Store)
            .where(Store.slug.not_in(desired_store_slugs))
            .values(is_active=False)
        )

    # 2. Menu Categories
    category_ids_by_slug: dict[str, object] = {}
    for c in bundle.categories:
        stmt = (
            insert(MenuCategory)
            .values(
                slug=c.slug,
                name_vi=c.name_vi,
                name_en=c.name_en,
                description_vi=c.description_vi,
                description_en=c.description_en,
                display_order=c.display_order,
                is_active=c.is_active,
            )
            .on_conflict_do_update(
                index_elements=[MenuCategory.slug],
                set_={
                    "name_vi": c.name_vi,
                    "name_en": c.name_en,
                    "description_vi": c.description_vi,
                    "description_en": c.description_en,
                    "display_order": c.display_order,
                    "is_active": c.is_active,
                },
            )
            .returning(MenuCategory.id)
        )
        category_ids_by_slug[c.slug] = (await session.execute(stmt)).scalar_one()

    # 3. Ingredients
    ingredient_ids_by_code: dict[str, object] = {}
    for ing in bundle.ingredients:
        stmt = (
            insert(Ingredient)
            .values(
                code=ing.code,
                name_vi=ing.name_vi,
                name_en=ing.name_en,
                allergen_code=ing.allergen_code,
            )
            .on_conflict_do_update(
                index_elements=[Ingredient.code],
                set_={
                    "name_vi": ing.name_vi,
                    "name_en": ing.name_en,
                    "allergen_code": ing.allergen_code,
                },
            )
            .returning(Ingredient.id)
        )
        ingredient_ids_by_code[ing.code] = (await session.execute(stmt)).scalar_one()

    # 4. Products, Variants & ProductIngredients
    product_ids_by_slug: dict[str, object] = {}
    variant_count = 0
    for p in bundle.products:
        category_id = category_ids_by_slug[p.category_slug]
        stmt = (
            insert(Product)
            .values(
                category_id=category_id,
                slug=p.slug,
                name_vi=p.name_vi,
                name_en=p.name_en,
                short_description_vi=p.short_description_vi,
                short_description_en=p.short_description_en,
                story_vi=p.story_vi,
                image_url=p.image_url,
                taste_tags=p.taste_tags,
                caffeine_level=p.caffeine_level,
                bitterness_level=p.bitterness_level,
                sweetness_level=p.sweetness_level,
                has_milk=p.has_milk,
                is_signature=p.is_signature,
                is_featured=p.is_featured,
                is_active=p.is_active,
                display_order=p.display_order,
            )
            .on_conflict_do_update(
                index_elements=[Product.slug],
                set_={
                    "category_id": category_id,
                    "name_vi": p.name_vi,
                    "name_en": p.name_en,
                    "short_description_vi": p.short_description_vi,
                    "short_description_en": p.short_description_en,
                    "story_vi": p.story_vi,
                    "image_url": p.image_url,
                    "taste_tags": p.taste_tags,
                    "caffeine_level": p.caffeine_level,
                    "bitterness_level": p.bitterness_level,
                    "sweetness_level": p.sweetness_level,
                    "has_milk": p.has_milk,
                    "is_signature": p.is_signature,
                    "is_featured": p.is_featured,
                    "is_active": p.is_active,
                    "display_order": p.display_order,
                },
            )
            .returning(Product.id)
        )
        product_id = (await session.execute(stmt)).scalar_one()
        product_ids_by_slug[p.slug] = product_id

        valid_sizes = [v.size for v in p.variants]
        await session.execute(
            delete(ProductVariant).where(
                ProductVariant.product_id == product_id,
                ProductVariant.size.not_in(valid_sizes),
            )
        )
        for v in p.variants:
            v_stmt = (
                insert(ProductVariant)
                .values(
                    product_id=product_id,
                    sku=v.sku,
                    size=v.size,
                    temperature=v.temperature,
                    price_vnd=v.price_vnd,
                    calories_kcal=v.calories_kcal,
                    is_available=v.is_available,
                )
                .on_conflict_do_update(
                    constraint="uq_product_variants_product_size",
                    set_={
                        "sku": v.sku,
                        "temperature": v.temperature,
                        "price_vnd": v.price_vnd,
                        "calories_kcal": v.calories_kcal,
                        "is_available": v.is_available,
                    },
                )
            )
            await session.execute(v_stmt)
            variant_count += 1

        desired_ing_ids = [ingredient_ids_by_code[i.code] for i in p.ingredients]
        if desired_ing_ids:
            await session.execute(
                delete(ProductIngredient).where(
                    ProductIngredient.product_id == product_id,
                    ProductIngredient.ingredient_id.not_in(desired_ing_ids),
                )
            )
        else:
            await session.execute(
                delete(ProductIngredient).where(ProductIngredient.product_id == product_id)
            )

        for ing in p.ingredients:
            pi_stmt = (
                insert(ProductIngredient)
                .values(
                    product_id=product_id,
                    ingredient_id=ingredient_ids_by_code[ing.code],
                    is_optional=ing.is_optional,
                )
                .on_conflict_do_update(
                    index_elements=[ProductIngredient.product_id, ProductIngredient.ingredient_id],
                    set_={"is_optional": ing.is_optional},
                )
            )
            await session.execute(pi_stmt)

    # 5. Promotions & PromotionProducts
    for promo in bundle.promotions:
        stmt = (
            insert(Promotion)
            .values(
                slug=promo.slug,
                title_vi=promo.title_vi,
                title_en=promo.title_en,
                summary_vi=promo.summary_vi,
                conditions_vi=promo.conditions_vi,
                promo_code=promo.promo_code,
                discount_type=promo.discount_type,
                discount_value=promo.discount_value,
                banner_image_url=promo.banner_image_url,
                start_at=promo.start_at,
                end_at=promo.end_at,
                is_active=promo.is_active,
            )
            .on_conflict_do_update(
                index_elements=[Promotion.slug],
                set_={
                    "title_vi": promo.title_vi,
                    "title_en": promo.title_en,
                    "summary_vi": promo.summary_vi,
                    "conditions_vi": promo.conditions_vi,
                    "promo_code": promo.promo_code,
                    "discount_type": promo.discount_type,
                    "discount_value": promo.discount_value,
                    "banner_image_url": promo.banner_image_url,
                    "start_at": promo.start_at,
                    "end_at": promo.end_at,
                    "is_active": promo.is_active,
                },
            )
            .returning(Promotion.id)
        )
        promo_id = (await session.execute(stmt)).scalar_one()

        desired_p_ids = [product_ids_by_slug[slug] for slug in promo.product_slugs]
        if desired_p_ids:
            await session.execute(
                delete(PromotionProduct).where(
                    PromotionProduct.promotion_id == promo_id,
                    PromotionProduct.product_id.not_in(desired_p_ids),
                )
            )
        else:
            await session.execute(
                delete(PromotionProduct).where(PromotionProduct.promotion_id == promo_id)
            )
        for p_id in desired_p_ids:
            pp_stmt = (
                insert(PromotionProduct)
                .values(promotion_id=promo_id, product_id=p_id)
                .on_conflict_do_nothing()
            )
            await session.execute(pp_stmt)

    await session.flush()

    # Verify total active counts in DB
    stores_total = len(
        (await session.execute(select(Store.id).where(Store.is_active.is_(True)))).all()
    )
    categories_total = len((await session.execute(select(MenuCategory.id))).all())
    ingredients_total = len((await session.execute(select(Ingredient.id))).all())
    products_total = len((await session.execute(select(Product.id))).all())
    promotions_total = len((await session.execute(select(Promotion.id))).all())

    return {
        "stores": stores_total,
        "categories": categories_total,
        "ingredients": ingredients_total,
        "products": products_total,
        "variants": variant_count,
        "promotions": promotions_total,
    }


async def run_seed(seed_dir: Path, database_url: str) -> dict[str, int]:
    bundle = load_seed_bundle(seed_dir)
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session, session.begin():
            summary = await upsert_bundle(session, bundle)
        return summary
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed BREW & BEAN data into PostgreSQL.")
    parser.add_argument(
        "--seed-dir",
        type=Path,
        default=REPO_ROOT / "data" / "seed",
        help="Path to directory containing seed JSON files.",
    )
    args = parser.parse_args()

    summary = asyncio.run(run_seed(args.seed_dir, settings.MIGRATION_DATABASE_URL))
    print("[BREW & BEAN] Seed database hoàn tất (idempotent upsert):")
    for key, val in summary.items():
        print(f"  - {key}: {val}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
