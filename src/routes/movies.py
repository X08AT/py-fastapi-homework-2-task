import datetime
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from database import get_db, MovieModel
from database.models import (
    CountryModel,
    GenreModel,
    ActorModel,
    LanguageModel,
    MovieStatusEnum,
)
from schemas.movies import (
    MovieCreate,
    MovieDetailSchema,
    MovieList,
    MovieUpdate,
)

router = APIRouter()


@router.get("/movies/", response_model=MovieList)
async def get_movies(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=20),
):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(MovieModel).offset(offset).limit(per_page).order_by(MovieModel.id.desc())
    )
    movies = result.scalars().all()

    if not movies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No movies found."
        )

    result = await db.execute(select(func.count()).select_from(MovieModel))

    total_items = result.scalar()
    total_pages = math.ceil(total_items / per_page)

    next_page = None
    prev_page = None

    if page > 1:
        prev_page = f"/theater/movies/?page={page - 1}&per_page={per_page}"
    if page < total_pages:
        next_page = f"/theater/movies/?page={page + 1}&per_page={per_page}"

    return {
        "movies": movies,
        "prev_page": prev_page,
        "next_page": next_page,
        "total_pages": total_pages,
        "total_items": total_items,
    }


@router.post("/movies/", response_model=MovieDetailSchema, status_code=201)
async def create_movie(movie: MovieCreate, db: AsyncSession = Depends(get_db)):
    if movie.date > datetime.date.today() + datetime.timedelta(days=365):
        raise HTTPException(status_code=400, detail="Invalid input data.")

    result = await db.execute(
        select(MovieModel).where(
            MovieModel.name == movie.name,
            MovieModel.date == movie.date,
        )
    )
    existing_movie = result.scalar_one_or_none()

    if existing_movie:
        raise HTTPException(
            status_code=409,
            detail=f"A movie with the name '{movie.name}' "
            f"and release date '{movie.date}' already exists.",
        )

    result = await db.execute(
        select(CountryModel).where(
            CountryModel.code == movie.country,
        )
    )

    country = result.scalar_one_or_none()

    if country is None:
        country = CountryModel(code=movie.country)
        db.add(country)
        await db.flush()

    new_movie = MovieModel(
        name=movie.name,
        date=movie.date,
        score=movie.score,
        overview=movie.overview,
        status=movie.status,
        budget=movie.budget,
        revenue=movie.revenue,
        country=country,
    )

    genres = []

    for genre_name in movie.genres:
        result = await db.execute(
            select(GenreModel).where(
                GenreModel.name == genre_name,
            )
        )

        genre = result.scalar_one_or_none()

        if genre is None:
            genre = GenreModel(name=genre_name)
            db.add(genre)
            await db.flush()

        genres.append(genre)

    new_movie.genres = genres

    actors = []

    for actor_name in movie.actors:
        result = await db.execute(
            select(ActorModel).where(
                ActorModel.name == actor_name,
            )
        )

        actor = result.scalar_one_or_none()

        if actor is None:
            actor = ActorModel(name=actor_name)
            db.add(actor)
            await db.flush()

        actors.append(actor)

    new_movie.actors = actors

    languages = []
    for language_name in movie.languages:
        result = await db.execute(
            select(LanguageModel).where(
                LanguageModel.name == language_name,
            )
        )

        language = result.scalar_one_or_none()

        if language is None:
            language = LanguageModel(name=language_name)
            db.add(language)
            await db.flush()

        languages.append(language)

    new_movie.languages = languages

    db.add(new_movie)

    await db.commit()

    result = await db.execute(
        select(MovieModel)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
        .where(MovieModel.id == new_movie.id)
    )

    new_movie = result.scalar_one()

    return new_movie


@router.get("/movies/{movie_id}/", response_model=MovieDetailSchema)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MovieModel)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
        .where(
            MovieModel.id == movie_id,
        )
    )

    movie = result.scalar_one_or_none()

    if movie is None:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )

    return movie


@router.delete("/movies/{movie_id}/", status_code=204)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MovieModel).where(
            MovieModel.id == movie_id,
        )
    )
    movie = result.scalar_one_or_none()

    if movie is None:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )

    await db.delete(movie)
    await db.commit()


@router.patch("/movies/{movie_id}/", status_code=200)
async def update_movie(
    movie_id: int, movie_data: MovieUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(MovieModel).where(
            MovieModel.id == movie_id,
        )
    )

    movie = result.scalar_one_or_none()

    if movie is None:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )

    update_data = movie_data.model_dump(exclude_unset=True)

    if "score" in update_data and not 0 <= update_data["score"] <= 100:
        raise HTTPException(
            status_code=400,
            detail="Invalid input data.",
        )

    if "budget" in update_data and update_data["budget"] < 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid input data.",
        )

    if "revenue" in update_data and update_data["revenue"] < 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid input data.",
        )

    for field, value in update_data.items():
        if field == "status":
            value = MovieStatusEnum(value)

        setattr(movie, field, value)

    await db.commit()

    return {"detail": "Movie updated successfully."}
