from __future__ import annotations

import re

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
from rag.text.normalize import strip_vietnamese_accents


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
        self,
        parsed: ParsedQuery,
        limit: int = 5,
        *,
        exact_only: bool = False,
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
            for term in parsed.search_terms[:14]
        ]

        stmt = (
            self._base_product_stmt()
            .where(or_(name_trgm >= 0.45, *term_clauses))
            .order_by(name_trgm.desc(), Product.display_order)
            .limit(max(limit * 4, 16))
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        if not rows:
            return []

        # 1. Check for exact full-name / slug phrase matches in the user's query first
        exact_matches: list[tuple[int, int, tuple[int, int], Product]] = []
        for prod in rows:
            aliases = {
                strip_vietnamese_accents(prod.name_vi.lower()),
                strip_vietnamese_accents(prod.name_en.lower()),
                prod.slug.replace("-", " ").lower(),
            }
            best_span: tuple[int, int] | None = None
            for alias in aliases:
                clean_alias = alias.strip()
                if len(clean_alias) < 4:
                    continue
                m = re.search(rf"\b{re.escape(clean_alias)}\b", parsed.ascii_query)
                if m is not None:
                    span = (m.start(), m.end())
                    if best_span is None or (span[1] - span[0]) > (best_span[1] - best_span[0]):
                        best_span = span
            if best_span is not None:
                span_len = best_span[1] - best_span[0]
                exact_matches.append((best_span[0], -span_len, best_span, prod))

        if exact_matches:
            # Sort longest spans first to prune strict substring overlaps (e.g. "sua hanh nhan"
            # inside "matcha sua hanh nhan"), then restore mention order in the query.
            by_len = sorted(exact_matches, key=lambda item: (-item[1], item[0]), reverse=True)
            kept: list[tuple[int, Product, tuple[int, int]]] = []
            for start_pos, _neg_len, span, prod in by_len:
                is_subspan = any(
                    span[0] >= prev_span[0]
                    and span[1] <= prev_span[1]
                    and span != prev_span
                    for _p_pos, _p_prod, prev_span in kept
                )
                if not is_subspan:
                    kept.append((start_pos, prod, span))
            kept.sort(key=lambda item: (item[0], item[1].display_order))
            return [build_product_detail(prod) for _pos, prod, _span in kept[:limit]]

        if exact_only:
            return []

        # 2. Fallback: score candidates by how many search terms match their name/slug
        scored: list[tuple[int, float, Product]] = []
        for prod in rows:
            slug_text = prod.slug.replace("-", " ")
            haystack = f"{slug_text} {prod.name_en.lower()} {prod.name_vi.lower()}"
            haystack_ascii = strip_vietnamese_accents(haystack)
            haystack_tokens = set(re.findall(r"[a-z0-9]+", haystack_ascii))
            hits = sum(
                1 for t in parsed.search_terms if t in haystack_tokens or t in haystack_ascii
            )
            if hits > 0:
                name_vi_tokens = [
                    tok
                    for tok in re.findall(
                        r"[a-z0-9]+", strip_vietnamese_accents(prod.name_vi.lower())
                    )
                    if len(tok) >= 2
                ]
                coverage = (
                    sum(1 for tok in name_vi_tokens if tok in parsed.ascii_query)
                    / max(1, len(name_vi_tokens))
                )
                scored.append((hits, coverage, prod))

        scored.sort(key=lambda item: (item[0], item[1], -item[2].display_order), reverse=True)
        if not scored:
            return []
        top_hits, top_cov, _ = scored[0]
        if top_hits >= 2 and top_cov >= 0.65:
            filtered = [
                p
                for hits, cov, p in scored
                if hits >= max(2, top_hits - 1) and cov >= 0.5
            ][:limit]
        else:
            filtered = [p for hits, _cov, p in scored if hits >= max(1, top_hits - 1)][:limit]
        return [build_product_detail(p) for p in filtered]

    async def search_products(
        self, parsed: ParsedQuery, limit: int = 6
    ) -> list[ProductDetailOut]:
        """Search products using structured SQL filters."""
        if parsed.max_sweetness is not None:
            stmt = self._base_product_stmt().order_by(
                Product.sweetness_level.asc(),
                Product.is_signature.desc(),
                Product.display_order,
                Product.name_vi,
            )
        else:
            stmt = self._base_product_stmt().order_by(
                Product.is_signature.desc(), Product.display_order, Product.name_vi
            )

        if parsed.category_slug:
            stmt = stmt.where(MenuCategory.slug == parsed.category_slug)
        elif parsed.drinks_only:
            stmt = stmt.where(MenuCategory.slug != "pastry")

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

        if parsed.max_sweetness is not None:
            # Include natural low-sweetness drinks (<= 2) plus gentle 3/5 items if needed
            stmt = stmt.where(Product.sweetness_level <= max(3, parsed.max_sweetness))

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
                max_sweetness=parsed.max_sweetness,
                caffeine_level=parsed.caffeine_level,
                has_milk=parsed.has_milk,
                excluded_allergens=parsed.excluded_allergens,
                requested_size=parsed.requested_size,
                is_signature_only=parsed.is_signature_only,
                store_hint=parsed.store_hint,
                drinks_only=parsed.drinks_only,
                search_terms=[],
            )
            return await self.search_products(fallback_parsed, limit=limit)

        if parsed.taste_tags and products:
            products.sort(
                key=lambda p: (
                    sum(1 for t in parsed.taste_tags if t in (p.taste_tags or [])),
                    -p.sweetness_level if parsed.max_sweetness is not None else 0,
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
