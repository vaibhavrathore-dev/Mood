"""Simple, explainable content-based recommendations, without external ML APIs."""
from .models import Movie

GENRE_TARGETS = {
    'Action/thrill': {'Action', 'Thriller'},
    'Romance': {'Romance'},
    'Something scary': {'Horror'},
    'Mind-bending sci-fi': {'Sci-Fi'},
}
EXPLANATIONS = {
    'Action/thrill': 'Movies tagged Action or Thriller, ranked by genre overlap.',
    'Romance': 'Romantic movies from the curated catalog.',
    'Something scary': 'Horror movies for a scary watch.',
    'Mind-bending sci-fi': 'Science-fiction movies, with a small bonus for thrillers.',
    'A classic': 'Movies from 2000 or earlier, ordered chronologically.',
    'Hidden gems': 'Hand-picked titles from the Underrated collection.',
}


def rank_recommendations(movies: list[Movie], mood: str, language: str | None, limit: int):
    if language and language.strip().lower() != 'any':
        movies = [m for m in movies if m.language.casefold() == language.strip().casefold()]

    if mood == 'A classic':
        matches = [m for m in movies if m.year <= 2000]
        matches.sort(key=lambda m: (m.year, m.title.casefold()))
    elif mood == 'Hidden gems':
        matches = [m for m in movies if m.section == 'Underrated']
        matches.sort(key=lambda m: m.title.casefold())
    else:
        target = GENRE_TARGETS[mood]
        matches = [m for m in movies if target.intersection(m.genres)]

        def score(m: Movie):
            overlap = len(target.intersection(m.genres))
            bonus = int(mood == 'Mind-bending sci-fi' and 'Thriller' in m.genres)
            return overlap * 10 + bonus

        matches.sort(key=lambda m: (-score(m), m.title.casefold()))
    return matches[:limit], EXPLANATIONS[mood]
