from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.models.menu import Product
from app.repositories.menu_repo import MenuRepository, ProductFilterParams
from app.schemas.menu import (
    CategoryListResponse,
    CategoryOut,
    CategorySummaryOut,
    ProductDetailOut,
    ProductIngredientOut,
    ProductListResponse,
    ProductSummaryOut,
    ProductVariantOut,
)


def _extract_product_prices_and_allergens(
    product: Product,
) -> tuple[int, int, list[str], list[ProductVariantOut]]:
    variants = [ProductVariantOut.model_validate(v) for v in product.variants]
    available_prices = [v.price_vnd for v in variants if v.is_available]
    all_prices = available_prices or [v.price_vnd for v in variants]
    min_price = min(all_prices) if all_prices else 0
    max_price = max(all_prices) if all_prices else 0

    allergens = sorted(
        {
            pi.ingredient.allergen_code
            for pi in product.product_ingredients
            if pi.ingredient.allergen_code
        }
    )
    return min_price, max_price, allergens, variants


def build_product_summary(product: Product) -> ProductSummaryOut:
    min_price, max_price, allergens, variants = _extract_product_prices_and_allergens(product)
    return ProductSummaryOut(
        id=product.id,
        slug=product.slug,
        name_vi=product.name_vi,
        name_en=product.name_en,
        short_description_vi=product.short_description_vi,
        short_description_en=product.short_description_en,
        image_url=product.image_url,
        category=CategorySummaryOut.model_validate(product.category),
        taste_tags=list(product.taste_tags or []),
        caffeine_level=product.caffeine_level,  # type: ignore[arg-type]
        bitterness_level=product.bitterness_level,
        sweetness_level=product.sweetness_level,
        has_milk=product.has_milk,
        is_signature=product.is_signature,
        is_featured=product.is_featured,
        min_price_vnd=min_price,
        max_price_vnd=max_price,
        allergens=allergens,
        variants=variants,
    )


def build_product_detail(product: Product) -> ProductDetailOut:
    summary = build_product_summary(product)
    ingredients = [
        ProductIngredientOut(
            code=pi.ingredient.code,
            name_vi=pi.ingredient.name_vi,
            name_en=pi.ingredient.name_en,
            allergen_code=pi.ingredient.allergen_code,
            is_optional=pi.is_optional,
        )
        for pi in sorted(product.product_ingredients, key=lambda item: item.ingredient.code)
    ]
    return ProductDetailOut(
        **summary.model_dump(),
        story_vi=product.story_vi,
        ingredients=ingredients,
    )


class MenuService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = MenuRepository(session)

    async def list_categories(self) -> CategoryListResponse:
        rows = await self.repo.list_categories_with_counts()
        items = [
            CategoryOut(
                id=cat.id,
                slug=cat.slug,
                name_vi=cat.name_vi,
                name_en=cat.name_en,
                description_vi=cat.description_vi,
                description_en=cat.description_en,
                display_order=cat.display_order,
                product_count=count,
            )
            for cat, count in rows
        ]
        return CategoryListResponse(items=items, total=len(items))

    async def list_products(self, filters: ProductFilterParams) -> ProductListResponse:
        products = await self.repo.list_products(filters)
        items = [build_product_summary(p) for p in products]
        return ProductListResponse(items=items, total=len(items))

    async def get_product_detail(self, slug: str) -> ProductDetailOut:
        product = await self.repo.get_product_by_slug(slug)
        if product is None:
            raise ResourceNotFoundError(f"Không tìm thấy sản phẩm '{slug}'.")
        return build_product_detail(product)
