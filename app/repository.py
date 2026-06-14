import re
from typing import Any

from sqlalchemy import Select, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Policy, Product, Review
from app.schemas import SourceRecord
from app.sql_safety import validate_read_only_sql


def _like(term: str) -> str:
    return f"%{term.strip()}%"


STOPWORDS = {
    "about",
    "across",
    "best",
    "can",
    "compare",
    "does",
    "for",
    "give",
    "have",
    "how",
    "information",
    "into",
    "need",
    "price",
    "prices",
    "product",
    "products",
    "recommend",
    "show",
    "summarize",
    "tell",
    "the",
    "what",
    "with",
    "your",
}


def _terms(query: str) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9]+", query.lower())
    return [word for word in words if len(word) > 2 and word not in STOPWORDS][:8]


async def search_products(session: AsyncSession, query: str, limit: int = 6) -> list[Product]:
    terms = _terms(query)
    if not terms:
        return []
    stmt: Select[tuple[Product]] = select(Product).limit(limit)
    clauses = []
    for term in terms:
        clauses.extend(
            [
                Product.name.ilike(_like(term)),
                Product.brand.ilike(_like(term)),
                Product.category.ilike(_like(term)),
                Product.features.ilike(_like(term)),
            ]
        )
    stmt = stmt.where(or_(*clauses))
    result = await session.execute(
        stmt.order_by(Product.inventory_count.desc(), Product.price.asc())
    )
    return list(result.scalars().all())


async def get_product_reviews(session: AsyncSession, query: str, limit: int = 12) -> list[Review]:
    products = await search_products(session, query, limit=3)
    skus = [product.sku for product in products]
    terms = _terms(query)
    stmt = select(Review).limit(limit)
    clauses = []
    if skus:
        clauses.append(Review.product_sku.in_(skus))
    for term in terms:
        clauses.extend(
            [
                Review.product_sku.ilike(_like(term)),
                Review.title.ilike(_like(term)),
                Review.body.ilike(_like(term)),
            ]
        )
    if not clauses:
        return []
    result = await session.execute(stmt.where(or_(*clauses)).order_by(Review.rating.desc()))
    return list(result.scalars().all())


async def search_policies(session: AsyncSession, query: str, limit: int = 5) -> list[Policy]:
    terms = _terms(query)
    if not terms:
        return []
    stmt: Select[tuple[Policy]] = select(Policy).limit(limit)
    clauses = []
    for term in terms:
        clauses.extend(
            [
                Policy.topic.ilike(_like(term)),
                Policy.question.ilike(_like(term)),
                Policy.answer.ilike(_like(term)),
            ]
        )
    result = await session.execute(stmt.where(or_(*clauses)))
    return list(result.scalars().all())


async def run_safe_sql(session: AsyncSession, sql: str, limit: int = 25) -> list[dict[str, Any]]:
    safe_sql = validate_read_only_sql(sql)
    limited_sql = safe_sql if " limit " in safe_sql.lower() else f"{safe_sql} LIMIT {limit}"
    result = await session.execute(text(limited_sql))
    return [dict(row._mapping) for row in result.fetchall()]


def product_sources(products: list[Product]) -> list[SourceRecord]:
    return [
        SourceRecord(table="products", id=product.sku, label=f"{product.brand} {product.name}")
        for product in products
    ]


def review_sources(reviews: list[Review]) -> list[SourceRecord]:
    return [
        SourceRecord(
            table="reviews",
            id=str(review.id),
            label=f"{review.product_sku}: {review.title}",
        )
        for review in reviews
    ]


def policy_sources(policies: list[Policy]) -> list[SourceRecord]:
    return [
        SourceRecord(
            table="policies",
            id=str(policy.id),
            label=f"{policy.topic}: {policy.question[:60]}",
        )
        for policy in policies
    ]
