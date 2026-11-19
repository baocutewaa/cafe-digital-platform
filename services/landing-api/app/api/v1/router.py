from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import storefront

api_router = APIRouter()
api_router.include_router(storefront.router)
