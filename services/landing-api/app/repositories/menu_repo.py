from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.menu import (
    MenuCategory,
    Product,
    ProductIngredient,
    ProductVariant,
)


@dataclass(slots=True)
class ProductFilterParams:
    category: str | None = None
    max_price: int | None = None
    caffeine_level: str | None = None
    has_milk: bool | None = None
    taste_tag: str | None = None
    signature: bool | None = None
    featured: bool | None = None
    q: str | None = None


class MenuRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_categories_with_counts(self) -> list[tuple[MenuCategory, int]]:
        stmt = (
            select(MenuCategory, func.count(Product.id))
            .outerjoin(
                Product,
                and_(
                    Product.category_id == MenuCategory.id,
                    Product.is_active.is_(True),
                ),
            )
            .where(MenuCategory.is_active.is_(True))
            .group_by(MenuCategory.id)
            .order_by(MenuCategory.display_order, MenuCategory.name_vi)
        )
        result = await self.session.execute(stmt)
        return [(row[0], int(row[1])) for row in result.all()]

    async def list_products(self, filters: ProductFilterParams) -> list[Product]:
        stmt = (
            select(Product)
            .join(MenuCategory, Product.category_id == MenuCategory.id)
            .where(Product.is_active.is_(True), MenuCategory.is_active.is_(True))
            .options(
                selectinload(Product.category),
                selectinload(Product.variants),
                selectinload(Product.product_ingredients).selectinload(
                    ProductIngredient.ingredient
                ),
            )
            .order_by(Product.display_order, Product.name_vi)
        )

        if filters.category:
            stmt = stmt.where(MenuCategory.slug == filters.category.strip().lower())

        if filters.max_price is not None:
            stmt = stmt.where(
                Product.variants.any(
                    and_(
                        ProductVariant.is_available.is_(True),
                        ProductVariant.price_vnd <= filters.max_price,
                    )
                )
            )

        if filters.caffeine_level:
            stmt = stmt.where(Product.caffeine_level == filters.caffeine_level.strip().lower())

        if filters.has_milk is not None:
            stmt = stmt.where(Product.has_milk.is_(filters.has_milk))

        if filters.taste_tag:
            normalized_tag = filters.taste_tag.strip().lower()
            stmt = stmt.where(Product.taste_tags.contains([normalized_tag]))

        if filters.signature is not None:
            stmt = stmt.where(Product.is_signature.is_(filters.signature))

        if filters.featured is not None:
            stmt = stmt.where(Product.is_featured.is_(filters.featured))

        if filters.q and filters.q.strip():
            pattern = f"%{filters.q.strip()}%"
            unaccent_pattern = func.unaccent(pattern)
            stmt = stmt.where(
                or_(
                    func.unaccent(Product.name_vi).ilike(unaccent_pattern),
                    func.unaccent(Product.name_en).ilike(unaccent_pattern),
                    func.unaccent(Product.short_description_vi).ilike(unaccent_pattern),
                    func.unaccent(func.coalesce(Product.short_description_en, "")).ilike(
                        unaccent_pattern
                    ),
                )
            )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_product_by_slug(self, slug: str) -> Product | None:
        stmt = (
            select(Product)
            .join(MenuCategory, Product.category_id == MenuCategory.id)
            .where(
                Product.slug == slug,
                Product.is_active.is_(True),
                MenuCategory.is_active.is_(True),
            )
            .options(
                selectinload(Product.category),
                selectinload(Product.variants),
                selectinload(Product.product_ingredients).selectinload(
                    ProductIngredient.ingredient
                ),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_active_categories(self) -> int:
        stmt = select(func.count(MenuCategory.id)).where(MenuCategory.is_active.is_(True))
        return int((await self.session.execute(stmt)).scalar_one())

    async def count_active_products(self) -> int:
        stmt = select(func.count(Product.id)).where(Product.is_active.is_(True))
        return int((await self.session.execute(stmt)).scalar_one())
