import argparse
import asyncio

import pandas as pd
from sqlalchemy import delete

from app.db import SessionLocal, init_db
from app.models import Policy, Product, Review
from app.pii import redact_pii


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import SmartShopAI CSV data.")
    parser.add_argument("--products", default="data/products.csv")
    parser.add_argument("--reviews", default="data/reviews.csv")
    parser.add_argument("--policies", default="data/policies.csv")
    return parser.parse_args()


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized.columns = [str(column).strip().lower() for column in normalized.columns]
    return normalized


def product_records(products: pd.DataFrame) -> list[Product]:
    rows = []
    for row in products.to_dict(orient="records"):
        rows.append(
            Product(
                sku=str(row.get("sku") or row.get("id")),
                name=str(row["name"]),
                brand=str(row["brand"]),
                category=str(row["category"]),
                price=float(row["price"]),
                features=str(row.get("features") or row.get("description") or ""),
                inventory_count=int(row.get("inventory_count") or row.get("stock") or 0),
            )
        )
    return rows


def review_records(reviews: pd.DataFrame) -> list[Review]:
    rows = []
    for index, row in enumerate(reviews.to_dict(orient="records"), start=1):
        body = str(row.get("body") or row.get("text") or "")
        title = str(row.get("title") or body[:80] or f"Review {index}")
        rows.append(
            Review(
                product_sku=str(row.get("product_sku") or row.get("product_id")),
                rating=round(float(row["rating"])),
                title=redact_pii(title)[0],
                body=redact_pii(body)[0],
            )
        )
    return rows


def policy_records(policies: pd.DataFrame) -> list[Policy]:
    rows = []
    for row in policies.to_dict(orient="records"):
        topic = str(row.get("topic") or row.get("policy_type"))
        question = str(row.get("question") or row.get("description") or topic)
        answer = row.get("answer")
        if answer is None:
            conditions = str(row.get("conditions") or "").replace("|", "; ")
            timeframe = row.get("timeframe")
            timeframe_text = f" Timeframe: {timeframe} days." if timeframe not in (None, "") else ""
            answer = f"{conditions}.{timeframe_text}".strip()
        rows.append(Policy(topic=topic, question=question, answer=str(answer)))
    return rows


async def import_data(args: argparse.Namespace) -> None:
    await init_db()
    products = normalize_columns(pd.read_csv(args.products))
    reviews = normalize_columns(pd.read_csv(args.reviews))
    policies = normalize_columns(pd.read_csv(args.policies))

    async with SessionLocal() as session:
        await session.execute(delete(Review))
        await session.execute(delete(Policy))
        await session.execute(delete(Product))

        session.add_all(product_records(products))
        session.add_all(review_records(reviews))
        session.add_all(policy_records(policies))
        await session.commit()


if __name__ == "__main__":
    asyncio.run(import_data(parse_args()))
