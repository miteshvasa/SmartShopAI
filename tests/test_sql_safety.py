import pytest

from app.sql_safety import UnsafeQueryError, validate_read_only_sql


def test_allows_read_only_select() -> None:
    assert validate_read_only_sql("select sku, price from products").startswith("select")


@pytest.mark.parametrize(
    "sql",
    [
        "delete from products",
        "select * from products; drop table products",
        "update products set price = 1",
        "select 1",
    ],
)
def test_blocks_unsafe_sql(sql: str) -> None:
    with pytest.raises(UnsafeQueryError):
        validate_read_only_sql(sql)
