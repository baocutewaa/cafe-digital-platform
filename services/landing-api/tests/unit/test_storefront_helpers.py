from __future__ import annotations

import sys
import uuid
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

from app.models.menu import Ingredient, MenuCategory, Product, ProductIngredient, ProductVariant
from app.models.store import StoreHour
from app.services.menu_service import build_product_detail, build_product_summary
from app.services.storefront_service import compute_store_open_status

VIETNAM_TZ = timezone(timedelta(hours=7))
REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _make_sample_hours() -> list[StoreHour]:
    store_id = uuid.uuid4()
    return [
        StoreHour(
            id=uuid.uuid4(),
            store_id=store_id,
            day_of_week=day,
            open_time=time(7, 0),
            close_time=time(22, 0),
            is_closed=(day == 6),
        )
        for day in range(7)
    ]


def test_compute_store_open_status_open_and_closed() -> None:
    hours = _make_sample_hours()
    # Monday 09:30 ICT -> open
    mon_open = datetime(2026, 11, 16, 9, 30, tzinfo=VIETNAM_TZ)
    is_open, today = compute_store_open_status(hours, now=mon_open)
    assert is_open is True
    assert today is not None
    assert today.day_of_week == 0

    # Monday 22:00 ICT -> closed (close_time is exclusive)
    mon_close = datetime(2026, 11, 16, 22, 0, tzinfo=VIETNAM_TZ)
    is_open_close, _ = compute_store_open_status(hours, now=mon_close)
    assert is_open_close is False

    # Sunday -> is_closed=True
    sun_noon = datetime(2026, 11, 22, 12, 0, tzinfo=VIETNAM_TZ)
    is_open_sun, today_sun = compute_store_open_status(hours, now=sun_noon)
    assert is_open_sun is False
    assert today_sun is not None
    assert today_sun.is_closed is True


def test_build_product_summary_and_detail_allergens_and_prices() -> None:
    cat = MenuCategory(
        id=uuid.uuid4(),
        slug="signature",
        name_vi="Món Đặc Trưng",
        name_en="Signature",
        display_order=1,
        is_active=True,
    )
    prod_id = uuid.uuid4()
    product = Product(
        id=prod_id,
        category_id=cat.id,
        slug="test-latte",
        name_vi="Latte Thử Nghiệm",
        name_en="Test Latte",
        short_description_vi="Mô tả ngắn",
        short_description_en="Short desc",
        story_vi="Câu chuyện đồ uống",
        image_url="/images/products/test.webp",
        taste_tags=["sweet", "creamy"],
        caffeine_level="medium",
        bitterness_level=2,
        sweetness_level=4,
        has_milk=True,
        is_signature=True,
        is_featured=True,
        is_active=True,
        display_order=1,
    )
    product.category = cat
    product.variants = [
        ProductVariant(
            id=uuid.uuid4(),
            product_id=prod_id,
            sku="TEST-S",
            size="small",
            temperature="both",
            price_vnd=45000,
            calories_kcal=150,
            is_available=True,
        ),
        ProductVariant(
            id=uuid.uuid4(),
            product_id=prod_id,
            sku="TEST-L",
            size="large",
            temperature="iced",
            price_vnd=59000,
            calories_kcal=220,
            is_available=False,
        ),
    ]
    ing1 = Ingredient(
        id=uuid.uuid4(),
        code="fresh_milk",
        name_vi="Sữa tươi",
        name_en="Fresh Milk",
        allergen_code="DAIRY",
    )
    ing2 = Ingredient(
        id=uuid.uuid4(),
        code="arabica_caudat",
        name_vi="Arabica Cầu Đất",
        name_en="Cau Dat Arabica",
        allergen_code=None,
    )
    product.product_ingredients = [
        ProductIngredient(product_id=prod_id, ingredient_id=ing1.id, is_optional=False),
        ProductIngredient(product_id=prod_id, ingredient_id=ing2.id, is_optional=False),
    ]
    product.product_ingredients[0].ingredient = ing1
    product.product_ingredients[1].ingredient = ing2

    summary = build_product_summary(product)
    assert summary.min_price_vnd == 45000
    assert summary.max_price_vnd == 45000  # ignores unavailable large variant
    assert summary.allergens == ["DAIRY"]

    detail = build_product_detail(product)
    assert detail.story_vi == "Câu chuyện đồ uống"
    assert [i.code for i in detail.ingredients] == ["arabica_caudat", "fresh_milk"]


def test_seed_json_bundle_passes_pydantic_validation() -> None:
    from seed_database import load_seed_bundle

    bundle = load_seed_bundle(REPO_ROOT / "data" / "seed")
    assert len(bundle.stores) == 3
    assert len(bundle.categories) == 6
    assert 28 <= len(bundle.products) <= 32
    assert len(bundle.promotions) == 3

    for product in bundle.products:
        if not product.has_milk:
            # Ensure dairy-free consistency in seed data
            ing_codes = {i.code for i in product.ingredients if not i.is_optional}
            dairy_codes = {i.code for i in bundle.ingredients if i.allergen_code == "DAIRY"}
            assert ing_codes.isdisjoint(dairy_codes), (
                f"Product {product.slug} has has_milk=false but includes dairy "
                f"{ing_codes & dairy_codes}"
            )


def test_settings_normalizes_neon_ssl_urls() -> None:
    from app.core.config import Settings

    raw_neon = (
        "postgresql://user:pass@ep-cool.ap-southeast-1.aws.neon.tech/"
        "neondb?sslmode=require&channel_binding=require"
    )
    expected = (
        "postgresql+asyncpg://user:pass@ep-cool.ap-southeast-1.aws.neon.tech/"
        "neondb?ssl=require"
    )
    assert Settings.normalize_asyncpg_url(raw_neon) == expected
    local_url = "postgresql+asyncpg://cafe_owner:password@localhost:5432/cafe_db"
    assert Settings.normalize_asyncpg_url(local_url) == local_url
