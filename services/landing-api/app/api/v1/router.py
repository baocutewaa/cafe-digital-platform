from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import chat, menu, promotions, storefront, stores

api_router = APIRouter()
api_router.include_router(storefront.router)
api_router.include_router(stores.router)
api_router.include_router(menu.router)
api_router.include_router(promotions.router)
api_router.include_router(chat.router)
