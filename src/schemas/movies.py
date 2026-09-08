import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class MovieBaseList(BaseModel):
    id: int
    name: str
    date: datetime.date
    score: float
    overview: str


class MovieList(BaseModel):
    movies: List[MovieBaseList]
    prev_page: str | None = None
    next_page: str | None = None
    total_items: int
    total_pages: int

    model_config = {"from_attributes": True}


class MovieStatus(str, Enum):
    RELEASED = "Released"
    POST_PRODUCTION = "Post Production"
    IN_PRODUCTION = "In Production"


class MovieCreate(BaseModel):
    name: str = Field(max_length=255)
    date: datetime.date
    score: float = Field(ge=0, le=100)
    overview: str
    status: MovieStatus
    budget: float = Field(ge=0)
    revenue: float = Field(ge=0)
    country: str
    genres: List[str]
    actors: List[str]
    languages: List[str]


class CountryResponse(BaseModel):
    id: int
    code: str
    name: str | None


class GenreResponse(BaseModel):
    id: int
    name: str


class ActorResponse(BaseModel):
    id: int
    name: str


class LanguageResponse(BaseModel):
    id: int
    name: str


class MovieDetailSchema(BaseModel):
    id: int
    name: str
    date: datetime.date
    score: float
    overview: str
    status: MovieStatus
    budget: float
    revenue: float
    country: CountryResponse
    genres: list[GenreResponse]
    actors: list[ActorResponse]
    languages: list[LanguageResponse]

    model_config = {"from_attributes": True}


class MovieUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    date: datetime.date | None = None
    score: float | None = Field(default=None, ge=0, le=100)
    overview: str | None = None
    status: MovieStatus | None = None
    budget: float | None = Field(default=None, ge=0)
    revenue: float | None = Field(default=None, ge=0)
