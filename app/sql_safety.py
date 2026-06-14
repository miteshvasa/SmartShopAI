import re

ALLOWED_TABLES = {"products", "reviews", "policies"}
DISALLOWED = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|merge|call|execute)\b",
    re.IGNORECASE,
)


class UnsafeQueryError(ValueError):
    pass


def validate_read_only_sql(sql: str) -> str:
    normalized = " ".join(sql.strip().split())
    if not normalized:
        raise UnsafeQueryError("SQL cannot be empty.")
    if ";" in normalized.rstrip(";"):
        raise UnsafeQueryError("Only one SQL statement is allowed.")
    normalized = normalized.rstrip(";")
    if not normalized.lower().startswith("select "):
        raise UnsafeQueryError("Only SELECT statements are allowed.")
    if DISALLOWED.search(normalized):
        raise UnsafeQueryError("Mutation or administrative statements are not allowed.")

    lowered = normalized.lower()
    mentioned = {table for table in ALLOWED_TABLES if re.search(rf"\b{table}\b", lowered)}
    if not mentioned:
        raise UnsafeQueryError("Query must reference an allowlisted table.")
    return normalized
