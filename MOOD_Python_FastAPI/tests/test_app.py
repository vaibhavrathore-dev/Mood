from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    api = create_app(f"sqlite:///{tmp_path / 'test_mood.db'}")
    with TestClient(api) as test_client:
        yield test_client


def test_health_and_seeded_catalog(client):
    assert client.get('/api/v1/health').json()['status'] == 'ok'
    response = client.get('/api/v1/movies')
    assert response.status_code == 200
    movies = response.json()
    assert len(movies) == 36
    assert len({movie['id'] for movie in movies}) == 36
    assert next(movie for movie in movies if movie['title'] == 'Inception')['imdb_rating'] == 8.8


def test_search_and_filters(client):
    assert [m['title'] for m in client.get('/api/v1/movies?search=inception').json()] == ['Inception']
    assert all('Horror' in m['genres'] for m in client.get('/api/v1/movies?genre=Horror').json())
    assert all(m['language'] == 'Japanese' for m in client.get('/api/v1/movies?language=Japanese').json())
    assert len(client.get('/api/v1/movies?section=Haunted%20Hours').json()) == 6
    assert client.get('/api/v1/movies?search=this-does-not-exist').json() == []
    assert 'Romance' in client.get('/api/v1/genres').json()


@pytest.mark.parametrize('mood,expected_genre', [
    ('Action/thrill','Action'),
    ('Romance','Romance'),
    ('Something scary','Horror'),
    ('Mind-bending sci-fi','Sci-Fi'),
])
def test_genre_recommendations(client, mood, expected_genre):
    result = client.post('/api/v1/recommendations',json={'mood':mood,'limit':20}).json()
    assert result['count'] > 0
    if mood == 'Action/thrill':
        assert all(('Action' in m['genres'] or 'Thriller' in m['genres']) for m in result['movies'])
    else:
        assert all(expected_genre in m['genres'] for m in result['movies'])


def test_recommendations_language_and_special_moods(client):
    result = client.post('/api/v1/recommendations',json={'mood':'Something scary','language':'Japanese'}).json()
    assert result['count'] == 1
    assert result['movies'][0]['title'] == 'Ringu'
    classics = client.post('/api/v1/recommendations',json={'mood':'A classic'}).json()['movies']
    assert all(m['year'] <= 2000 for m in classics)
    gems = client.post('/api/v1/recommendations',json={'mood':'Hidden gems'}).json()['movies']
    assert gems and all(m['section'] == 'Underrated' for m in gems)
    none = client.post('/api/v1/recommendations',json={'mood':'Romance','language':'Swedish'}).json()
    assert none['count'] == 0  # no fake language fallback
    assert client.post('/api/v1/recommendations',json={'mood':'Not a real mood'}).status_code == 422


def test_details_and_errors(client):
    detail = client.get('/api/v1/movies/inception-2010')
    assert detail.status_code == 200
    assert detail.json()['director'] == 'Christopher Nolan'
    assert client.get('/api/v1/movies/not-a-movie').status_code == 404
    assert client.get('/api/v1/movies?limit=101').status_code == 422


def test_wishlist_persists_and_isolated(client):
    first = {'X-Guest-ID':str(uuid4())}
    second = {'X-Guest-ID':str(uuid4())}
    assert client.get('/api/v1/wishlist',headers=first).json() == []
    assert client.post('/api/v1/wishlist/inception-2010',headers=first).status_code == 201
    assert client.post('/api/v1/wishlist/inception-2010',headers=first).json()['message'] == 'Already in wishlist'
    assert len(client.get('/api/v1/wishlist',headers=first).json()) == 1
    assert client.get('/api/v1/wishlist',headers=second).json() == []
    assert client.post('/api/v1/wishlist/missing',headers=first).status_code == 404
    assert client.delete('/api/v1/wishlist/inception-2010',headers=first).status_code == 200
    assert client.get('/api/v1/wishlist',headers=first).json() == []
    assert client.delete('/api/v1/wishlist/inception-2010',headers=first).status_code == 404
    assert client.get('/api/v1/wishlist',headers={'X-Guest-ID':'bad'}).status_code == 422


def test_frontend_served_by_fastapi(client):
    for url in ['/', '/script.js', '/style.css', '/movie.html', '/wishlist.html', '/logo.png']:
        assert client.get(url).status_code == 200, url
    assert 'id="recommend-form"' in client.get('/').text
    assert 'class="main-card"' in client.get('/').text
    assert 'class="hero"' in client.get('/').text
    assert '/api/v1' in client.get('/script.js').text
