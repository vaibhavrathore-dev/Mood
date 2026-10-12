"""Seed from the original frontend's movie cards, represented as an editable CSV."""
import csv
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Movie

DATA_FILE = Path(__file__).resolve().parents[1] / 'data' / 'movies.csv'


def seed_movies(engine):
    with Session(engine) as session:
        if session.scalar(select(Movie.id).limit(1)) is not None:
            return
        with DATA_FILE.open(encoding='utf-8', newline='') as stream:
            for row in csv.DictReader(stream):
                session.add(Movie(
                    id=row['id'], title=row['title'], year=int(row['year']),
                    content_rating=row['content_rating'],
                    genres=row['genres'].split('|'), language=row['language'],
                    section=row['section'], poster_url=row['poster_url'],
                    overview=row['overview'], director=row['director'] or None,
                    imdb_rating=float(row['imdb_rating']) if row['imdb_rating'] else None,
                ))
        session.commit()
