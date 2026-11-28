from __future__ import annotations

import time

from httpx import AsyncClient


async def test_storefront_overview_returns_seeded_stats(async_client: AsyncClient) -> None:
    resp = await async_client.get("/api/v1/storefront")
    assert resp.status_code == 200
    body = resp.json()
    assert body["brand_name"] == "BREW & BEAN"
    assert body["stats"]["stores_count"] == 3
    assert body["stats"]["categories_count"] == 6
    assert body["stats"]["products_count"] == 30
    assert body["stats"]["active_promotions_count"] == 3
    assert len(body["signature_products"]) == 5
    assert all(p["is_signature"] is True for p in body["signature_products"])
    assert len(body["active_promotions"]) == 3


async def test_stores_list_and_detail(async_client: AsyncClient) -> None:
    resp = await async_client.get("/api/v1/stores")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    for store in body["items"]:
        assert len(store["hours"]) == 7
        assert isinstance(store["is_open_now"], bool)

    detail_resp = await async_client.get("/api/v1/stores/brew-bean-nguyen-dinh-thi")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["slug"] == "brew-bean-nguyen-dinh-thi"

    missing_resp = await async_client.get("/api/v1/stores/non-existent-store")
    assert missing_resp.status_code == 404


async def test_menu_categories_with_counts(async_client: AsyncClient) -> None:
    resp = await async_client.get("/api/v1/menu/categories")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 6
    total_products = sum(item["product_count"] for item in body["items"])
    assert total_products == 30


async def test_menu_products_multidimensional_filters(async_client: AsyncClient) -> None:
    # 1. All products
    all_resp = await async_client.get("/api/v1/menu/products")
    assert all_resp.status_code == 200
    assert all_resp.json()["total"] == 30

    # 2. Category filter
    cb_resp = await async_client.get("/api/v1/menu/products", params={"category": "cold-brew"})
    assert cb_resp.status_code == 200
    cb_items = cb_resp.json()["items"]
    assert len(cb_items) == 5
    assert all(item["category"]["slug"] == "cold-brew" for item in cb_items)

    # 3. max_price filter
    price_resp = await async_client.get("/api/v1/menu/products", params={"max_price": 40000})
    assert price_resp.status_code == 200
    price_items = price_resp.json()["items"]
    assert len(price_items) >= 5
    for item in price_items:
        assert item["min_price_vnd"] <= 40000
        assert any(v["is_available"] and v["price_vnd"] <= 40000 for v in item["variants"])

    # 4. caffeine_level filter
    caff_resp = await async_client.get("/api/v1/menu/products", params={"caffeine_level": "none"})
    assert caff_resp.status_code == 200
    caff_items = caff_resp.json()["items"]
    assert len(caff_items) >= 6
    assert all(item["caffeine_level"] == "none" for item in caff_items)

    # 5. has_milk=false filter
    nomilk_resp = await async_client.get("/api/v1/menu/products", params={"has_milk": "false"})
    assert nomilk_resp.status_code == 200
    nomilk_items = nomilk_resp.json()["items"]
    assert len(nomilk_items) >= 10
    assert all(item["has_milk"] is False for item in nomilk_items)

    # 6. taste_tag filter
    tag_resp = await async_client.get("/api/v1/menu/products", params={"taste_tag": "less_bitter"})
    assert tag_resp.status_code == 200
    tag_items = tag_resp.json()["items"]
    assert len(tag_items) >= 15
    assert all("less_bitter" in item["taste_tags"] for item in tag_items)

    # 7. signature filter
    sig_resp = await async_client.get("/api/v1/menu/products", params={"signature": "true"})
    assert sig_resp.status_code == 200
    assert sig_resp.json()["total"] == 5
    assert all(item["is_signature"] is True for item in sig_resp.json()["items"])

    # 8. Vietnamese unaccented keyword search (q)
    q_resp = await async_client.get("/api/v1/menu/products", params={"q": "ca phe muoi"})
    assert q_resp.status_code == 200
    q_slugs = [item["slug"] for item in q_resp.json()["items"]]
    assert "ca-phe-muoi-cau-dat" in q_slugs

    # 9. Combined filters
    combo_resp = await async_client.get(
        "/api/v1/menu/products",
        params={"max_price": 45000, "has_milk": "false", "taste_tag": "fruity"},
    )
    assert combo_resp.status_code == 200
    combo_items = combo_resp.json()["items"]
    assert len(combo_items) >= 2
    for item in combo_items:
        assert item["min_price_vnd"] <= 45000
        assert item["has_milk"] is False
        assert "fruity" in item["taste_tags"]


async def test_product_detail_and_allergens(async_client: AsyncClient) -> None:
    resp = await async_client.get("/api/v1/menu/products/ca-phe-muoi-cau-dat")
    assert resp.status_code == 200
    body = resp.json()
    assert body["slug"] == "ca-phe-muoi-cau-dat"
    assert body["story_vi"]
    assert len(body["variants"]) == 3
    assert "DAIRY" in body["allergens"]
    assert len(body["ingredients"]) >= 3

    dairy_free_resp = await async_client.get("/api/v1/menu/products/oat-milk-honey-latte")
    assert dairy_free_resp.status_code == 200
    assert "DAIRY" not in dairy_free_resp.json()["allergens"]

    not_found = await async_client.get("/api/v1/menu/products/non-existent-drink")
    assert not_found.status_code == 404


async def test_active_promotions(async_client: AsyncClient) -> None:
    resp = await async_client.get("/api/v1/promotions/active")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    for promo in body["items"]:
        assert promo["promo_code"]
        assert len(promo["products"]) > 0


async def test_storefront_endpoints_local_p95_latency(async_client: AsyncClient) -> None:
    # Warm up pool & cached AI status
    await async_client.get("/api/v1/storefront")

    endpoints = [
        "/api/v1/storefront",
        "/api/v1/stores",
        "/api/v1/menu/categories",
        "/api/v1/menu/products?max_price=50000&has_milk=false",
        "/api/v1/menu/products/ca-phe-muoi-cau-dat",
        "/api/v1/promotions/active",
    ]
    latencies_ms: list[float] = []
    for _ in range(5):
        for url in endpoints:
            t0 = time.perf_counter()
            r = await async_client.get(url)
            assert r.status_code == 200
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)

    latencies_ms.sort()
    p95_idx = int(len(latencies_ms) * 0.95) - 1
    p95_ms = latencies_ms[max(p95_idx, 0)]
    assert p95_ms < 150.0, f"Local p95 latency too high: {p95_ms:.2f} ms"
