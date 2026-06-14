from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    brand: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[str] = mapped_column(String(120), index=True)
    price: Mapped[float] = mapped_column(Float)
    features: Mapped[str] = mapped_column(Text)
    inventory_count: Mapped[int] = mapped_column(Integer, default=0)

    reviews: Mapped[list["Review"]] = relationship(back_populates="product")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_sku: Mapped[str] = mapped_column(ForeignKey("products.sku"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)

    product: Mapped[Product] = relationship(back_populates="reviews")


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String(120), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
