"""FastAPI app for the MOOD movie recommendation college project."""
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, get_db, make_engine
from .models import Movie, WishlistItem
from .recommender import rank_recommendations
from .schemas import MovieOut, RecommendationRequest, RecommendationResponse
from .seed import seed_movies

FRONTEND = Path(__file__).resolve().parents[1] / 'frontend'


def guest_uuid(x_guest_id: str = Header(description='Browser-local guest UUID')) -> str:
    try:
        return str(UUID(x_guest_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail='X-Guest-ID must be a valid UUID')


def create_app(db_url: str | None = None) -> FastAPI:
    engine = make_engine(db_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        Base.metadata.create_all(bind=engine)
        seed_movies(engine)
        yield
        engine.dispose()

    app = FastAPI(title='MOOD Movie Recommendation API', version='1.0.0', lifespan=lifespan,
                  description='A college demo with content-based movie recommendations, search, genres and guest wishlists.')
    app.state.engine = engine

    @app.get('/api/v1/health')
    def health():
        return {'status': 'ok', 'project': 'MOOD'}

    @app.get('/api/v1/movies', response_model=list[MovieOut])
    def movies_list(db: Session = Depends(get_db), search: str | None = Query(None, max_length=100),
                    genre: str | None = Query(None, max_length=50),
                    language: str | None = Query(None, max_length=50),
                    section: str | None = Query(None, max_length=70),
                    limit: int = Query(100, ge=1, le=100)):
        movies = db.scalars(select(Movie).order_by(Movie.title)).all()
        if search:
            needle = search.casefold().strip()
            movies = [m for m in movies if needle in m.title.casefold()
                      or any(needle in g.casefold() for g in m.genres)]
        if genre:
            movies = [m for m in movies if any(g.casefold() == genre.casefold() for g in m.genres)]
        if language:
            movies = [m for m in movies if m.language.casefold() == language.casefold()]
        if section:
            movies = [m for m in movies if m.section.casefold() == section.casefold()]
        return movies[:limit]

    @app.get('/api/v1/genres', response_model=list[str])
    def get_genres(db: Session = Depends(get_db)):
        movies = db.scalars(select(Movie)).all()
        return sorted({genre for m in movies for genre in m.genres})

    @app.get('/api/v1/languages', response_model=list[str])
    def get_languages(db: Session = Depends(get_db)):
        return sorted({m.language for m in db.scalars(select(Movie)).all()})

    @app.post('/api/v1/recommendations', response_model=RecommendationResponse)
    def recommend(payload: RecommendationRequest, db: Session = Depends(get_db)):
        catalog = list(db.scalars(select(Movie)).all())
        items, explanation = rank_recommendations(catalog, payload.mood, payload.language, payload.limit)
        return RecommendationResponse(mood=payload.mood, language=payload.language,
                                      explanation=explanation, count=len(items), movies=items)

    @app.get('/api/v1/wishlist', response_model=list[MovieOut])
    def get_wishlist(guest_id: str = Depends(guest_uuid), db: Session = Depends(get_db)):
        stmt = (select(Movie).join(WishlistItem, WishlistItem.movie_id == Movie.id)
                .where(WishlistItem.guest_id == guest_id).order_by(Movie.title))
        return list(db.scalars(stmt).all())

    @app.post('/api/v1/wishlist/{movie_id}', status_code=status.HTTP_201_CREATED)
    def add_wishlist(movie_id: str, guest_id: str = Depends(guest_uuid), db: Session = Depends(get_db)):
        if not db.get(Movie, movie_id):
            raise HTTPException(status_code=404, detail='Movie not found')
        if db.get(WishlistItem, (guest_id, movie_id)):
            return {'message': 'Already in wishlist', 'movie_id': movie_id}
        db.add(WishlistItem(guest_id=guest_id, movie_id=movie_id))
        db.commit()
        return {'message': 'Added to wishlist', 'movie_id': movie_id}

    @app.delete('/api/v1/wishlist/{movie_id}')
    def remove_wishlist(movie_id: str, guest_id: str = Depends(guest_uuid), db: Session = Depends(get_db)):
        item = db.get(WishlistItem, (guest_id, movie_id))
        if not item:
            raise HTTPException(status_code=404, detail='Wishlist entry not found')
        db.delete(item)
        db.commit()
        return {'message': 'Removed from wishlist', 'movie_id': movie_id}

    @app.get('/api/v1/movies/{movie_id}', response_model=MovieOut)
    def movie_detail(movie_id: str, db: Session = Depends(get_db)):
        movie = db.get(Movie, movie_id)
        if movie is None:
            raise HTTPException(status_code=404, detail='Movie not found')
        return movie

    @app.get('/', include_in_schema=False)
    def homepage():
        return FileResponse(FRONTEND / 'index.html')

    # Keep APIs and homepage above this mount; StaticFiles serves CSS/JS/images/pages.
    app.mount('/', StaticFiles(directory=FRONTEND, html=True), name='frontend')
    return app


app = create_app()
