from __future__ import annotations

import uuid
from datetime import time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class StoreHourOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day_of_week: int
    open_time: time
    close_time: time
    is_closed: bool


class StoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    address: str
    district: str | None = None
    city: str
    phone: str | None = None
    google_maps_url: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    amenities: list[str]
    image_url: str | None = None
    is_active: bool
    is_open_now: bool
    today_hours: StoreHourOut | None = None
    hours: list[StoreHourOut]


class StoreListResponse(BaseModel):
    items: list[StoreOut]
    total: int
