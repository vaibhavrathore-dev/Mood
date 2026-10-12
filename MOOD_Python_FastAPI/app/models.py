"""Two relational tables: movie catalog and per-browser guest wishlist."""
from sqlalchemy import ForeignKey, Integer, Float, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class Movie(Base):
    __tablename__ = 'movies'

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    content_rating: Mapped[str] = mapped_column(String(12), nullable=False)
    genres: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    section: Mapped[str] = mapped_column(String(70), nullable=False)
    poster_url: Mapped[str] = mapped_column(Text, nullable=False)
    overview: Mapped[str] = mapped_column(Text, nullable=False)
    director: Mapped[str | None] = mapped_column(String(120), nullable=True)
    imdb_rating: Mapped[float | None] = mapped_column(Float, nullable=True)


class WishlistItem(Base):
    __tablename__ = 'wishlist_items'

    guest_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    movie_id: Mapped[str] = mapped_column(ForeignKey('movies.id', ondelete='CASCADE'), primary_key=True)
