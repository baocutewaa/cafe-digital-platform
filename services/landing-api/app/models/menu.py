from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MenuCategory(Base):
    __tablename__ = "menu_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name_vi: Mapped[str] = mapped_column(String(120), nullable=False)
    name_en: Mapped[str] = mapped_column(String(120), nullable=False)
    description_vi: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    products: Mapped[list[Product]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "caffeine_level IN ('none', 'low', 'medium', 'high')",
            name="ck_products_caffeine_level",
        ),
        CheckConstraint(
            "bitterness_level BETWEEN 1 AND 5",
            name="ck_products_bitterness_level",
        ),
        CheckConstraint(
            "sweetness_level BETWEEN 1 AND 5",
            name="ck_products_sweetness_level",
        ),
        Index("idx_products_category_active", "category_id", "is_active"),
        Index("idx_products_taste_tags", "taste_tags", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("menu_categories.id"),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name_vi: Mapped[str] = mapped_column(String(150), nullable=False)
    name_en: Mapped[str] = mapped_column(String(150), nullable=False)
    short_description_vi: Mapped[str] = mapped_column(Text, nullable=False)
    short_description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    story_vi: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    taste_tags: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    caffeine_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
        server_default=text("'medium'"),
    )
    bitterness_level: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=3,
        server_default=text("3"),
    )
    sweetness_level: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=3,
        server_default=text("3"),
    )
    has_milk: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    is_signature: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    display_order: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    category: Mapped[MenuCategory] = relationship(back_populates="products")
    variants: Mapped[list[ProductVariant]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductVariant.price_vnd",
    )
    product_ingredients: Mapped[list[ProductIngredient]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )


class ProductVariant(Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        CheckConstraint("size IN ('small', 'regular', 'large')", name="ck_variants_size"),
        CheckConstraint(
            "temperature IN ('hot', 'iced', 'both')",
            name="ck_variants_temperature",
        ),
        CheckConstraint("price_vnd >= 0", name="ck_variants_price_vnd"),
        UniqueConstraint("product_id", "size", name="uq_product_variants_product_size"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    sku: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    size: Mapped[str] = mapped_column(String(20), nullable=False)
    temperature: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="both",
        server_default=text("'both'"),
    )
    price_vnd: Mapped[int] = mapped_column(Integer, nullable=False)
    calories_kcal: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    product: Mapped[Product] = relationship(back_populates="variants")


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name_vi: Mapped[str] = mapped_column(String(120), nullable=False)
    name_en: Mapped[str] = mapped_column(String(120), nullable=False)
    allergen_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    product_ingredients: Mapped[list[ProductIngredient]] = relationship(
        back_populates="ingredient",
        cascade="all, delete-orphan",
    )


class ProductIngredient(Base):
    __tablename__ = "product_ingredients"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.id", ondelete="CASCADE"),
        primary_key=True,
    )
    is_optional: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    product: Mapped[Product] = relationship(back_populates="product_ingredients")
    ingredient: Mapped[Ingredient] = relationship(back_populates="product_ingredients")
