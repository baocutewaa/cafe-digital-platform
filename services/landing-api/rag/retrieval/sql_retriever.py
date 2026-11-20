from __future__ import annotations

from sqlalchemy import and_, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.menu import (
    Ingredient,
    MenuCategory,
    Product,
    ProductIngredient,
    ProductVariant,
)
from app.repositories.promotion_repo import PromotionRepository
from app.repositories.store_repo import StoreRepository
from app.schemas.menu import ProductDetailOut
from app.schemas.promotion import PromotionOut
from app.schemas.store import StoreOut
from app.services.menu_service import build_product_detail
from app.services.storefront_service import build_promotion_out, build_store_out
from rag.retrieval.query_parser import ParsedQuery


class SqlProductRetriever:
    """Structured SQL retriever for products, allergens, stores, and promotions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.store_repo = StoreRepository(session)
        self.promo_repo = PromotionRepository(session)

    def _base_product_stmt(self):
        return (
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
        )

    async def find_products_by_name(
        self, parsed: ParsedQuery, limit: int = 5
    ) -> list[ProductDetailOut]:
        """Match specific product names/aliases using unaccent + pg_trgm similarity."""
        if not parsed.search_terms:
            return []

        name_trgm = func.greatest(
            func.word_similarity(parsed.ascii_query, func.unaccent(func.lower(Product.name_vi))),
            func.word_similarity(parsed.ascii_query, func.lower(Product.name_en)),
        )

        # Require at least one meaningful term hit in product name/slug OR strong trigram match
        term_clauses = [
            or_(
                func.unaccent(Product.name_vi).ilike(func.unaccent(f"%{term}%")),
                Product.name_en.ilike(f"%{term}%"),
                Product.slug.ilike(f"%{term}%"),
            )
            for term in parsed.search_terms[:8]
        ]

        stmt = (
            self._base_product_stmt()
            .where(or_(name_trgm >= 0.45, *term_clauses))
            .order_by(name_trgm.desc(), Product.display_order)
            .limit(limit * 3)
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        if not rows:
            return []

        # Score candidates by how many search terms match their name so exact hits come first
        scored: list[tuple[int, Product]] = []
        for prod in rows:
            haystack = f"{prod.slug} {prod.name_en.lower()} {prod.name_vi.lower()}"
            from rag.text.normalize import strip_vietnamese_accents

            haystack_ascii = strip_vietnamese_accents(haystack)
            hits = sum(1 for t in parsed.search_terms if t in haystack_ascii)
            if hits > 0:
                scored.append((hits, prod))

        scored.sort(key=lambda pair: (pair[0], -pair[1].display_order), reverse=True)
        if not scored:
            return []
        top_hits = scored[0][0]
        # Keep products matching the strongest hit tier (prevents noisy 1-word partial leaks)
        filtered = [p for hits, p in scored if hits >= max(1, top_hits - 1)][:limit]
        return [build_product_detail(p) for p in filtered]

    async def search_products(
        self, parsed: ParsedQuery, limit: int = 6
    ) -> list[ProductDetailOut]:
        """Search products using structured SQL filters."""
        stmt = self._base_product_stmt().order_by(
            Product.is_signature.desc(), Product.display_order, Product.name_vi
        )

        if parsed.category_slug:
            stmt = stmt.where(MenuCategory.slug == parsed.category_slug)

        if parsed.is_signature_only:
            stmt = stmt.where(Product.is_signature.is_(True))

        if parsed.max_price is not None:
            stmt = stmt.where(
                Product.variants.any(
                    and_(
                        ProductVariant.is_available.is_(True),
                        ProductVariant.price_vnd <= parsed.max_price,
                    )
                )
            )

        if parsed.caffeine_level:
            stmt = stmt.where(Product.caffeine_level == parsed.caffeine_level)

        if parsed.has_milk is not None:
            stmt = stmt.where(Product.has_milk.is_(parsed.has_milk))

        if parsed.max_bitterness is not None:
            stmt = stmt.where(Product.bitterness_level <= parsed.max_bitterness)

        if parsed.taste_tags:
            # Match at least one requested taste tag, prioritizing products matching more
            stmt = stmt.where(
                or_(*[Product.taste_tags.contains([tag]) for tag in parsed.taste_tags])
            )

        if parsed.excluded_allergens:
            stmt = stmt.where(
                not_(
                    Product.product_ingredients.any(
                        and_(
                            ProductIngredient.is_optional.is_(False),
                            ProductIngredient.ingredient.has(
                                Ingredient.allergen_code.in_(parsed.excluded_allergens)
                            ),
                        )
                    )
                )
            )
            if "DAIRY" in parsed.excluded_allergens:
                stmt = stmt.where(Product.has_milk.is_(False))

        products = list((await self.session.execute(stmt.limit(limit * 2))).scalars().all())

        # If exact filter combination yields 0, retry without taste_tag
        if not products and parsed.taste_tags:
            fallback_parsed = ParsedQuery(
                raw_query=parsed.raw_query,
                normalized_query=parsed.normalized_query,
                ascii_query=parsed.ascii_query,
                language=parsed.language,
                max_price=parsed.max_price,
                category_slug=parsed.category_slug,
                taste_tags=[],
                max_bitterness=parsed.max_bitterness,
                caffeine_level=parsed.caffeine_level,
                has_milk=parsed.has_milk,
                excluded_allergens=parsed.excluded_allergens,
                requested_size=parsed.requested_size,
                is_signature_only=parsed.is_signature_only,
                store_hint=parsed.store_hint,
                search_terms=[],
            )
            return await self.search_products(fallback_parsed, limit=limit)

        if parsed.taste_tags and products:
            products.sort(
                key=lambda p: (
                    sum(1 for t in parsed.taste_tags if t in (p.taste_tags or [])),
                    1 if p.is_signature else 0,
                    -p.display_order,
                ),
                reverse=True,
            )

        return [build_product_detail(p) for p in products[:limit]]

    async def search_stores(self, parsed: ParsedQuery) -> list[StoreOut]:
        stores = await self.store_repo.list_active_stores()
        store_outs = [build_store_out(s) for s in stores]
        if parsed.store_hint:
            from rag.text.normalize import strip_vietnamese_accents

            hint = parsed.store_hint.lower()
            matched = [
                s
                for s in store_outs
                if hint
                in strip_vietnamese_accents(f"{s.name} {s.address} {s.district or ''}").lower()
            ]
            if matched:
                return matched
        return store_outs

    async def search_promotions(self) -> list[PromotionOut]:
        promos = await self.promo_repo.list_active_promotions()
        return [build_promotion_out(p) for p in promos]
