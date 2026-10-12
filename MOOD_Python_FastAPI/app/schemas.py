from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Mood = Literal[
    'Action/thrill', 'Romance', 'Something scary',
    'Mind-bending sci-fi', 'A classic', 'Hidden gems'
]


class MovieOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    year: int
    content_rating: str
    genres: list[str]
    language: str
    section: str
    poster_url: str
    overview: str
    director: str | None = None
    imdb_rating: float | None = None


class RecommendationRequest(BaseModel):
    mood: Mood
    language: str | None = None
    limit: int = Field(default=6, ge=1, le=30)


class RecommendationResponse(BaseModel):
    mood: str
    language: str | None
    explanation: str
    count: int
    movies: list[MovieOut]
