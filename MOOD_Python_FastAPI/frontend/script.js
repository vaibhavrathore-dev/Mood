// Browser-side code calls the actual Python FastAPI routes; no API keys required.
const API = '/api/v1';

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  if (!response.ok) {
    let problem = `Request failed (${response.status})`;
    try { const details = await response.json(); problem = details.detail || problem; } catch (_) {}
    throw new Error(typeof problem === 'string' ? problem : JSON.stringify(problem));
  }
  return response.status === 204 ? null : response.json();
}

function getGuestId() {
  let value = localStorage.getItem('mood_guest_id');
  if (!value) {
    value = crypto.randomUUID();
    localStorage.setItem('mood_guest_id', value);
  }
  return value;
}

function guestHeaders() { return {'X-Guest-ID': getGuestId()}; }

function movieCard(movie, {removable = false, onRemove = null} = {}) {
  const card = document.createElement('article');
  card.className = 'card';
  const cover = document.createElement('div'); cover.className = 'cover';
  const poster = document.createElement('img');
  poster.src = movie.poster_url;
  poster.alt = `${movie.title} poster`;
  poster.loading = 'lazy';
  poster.addEventListener('error', () => {
    cover.replaceChildren();
    cover.classList.add('poster-fallback');
    cover.dataset.genre = movie.genres[0] || 'Drama';
    const fallback = document.createElement('div'); fallback.className = 'poster-fallback-content';
    const wordmark = document.createElement('span'); wordmark.className = 'poster-fallback-label'; wordmark.textContent = 'MOOD / CINEMA';
    const name = document.createElement('strong'); name.textContent = movie.title;
    const year = document.createElement('span'); year.className = 'poster-fallback-year'; year.textContent = movie.year;
    fallback.append(wordmark, name, year); cover.append(fallback);
  });
  cover.append(poster); card.append(cover);
  const title = document.createElement('h4'); title.textContent = `${movie.title} (${movie.year})`;
  card.append(title);
  const tags = document.createElement('ul'); tags.className = 'info-li';
  for (const tag of [movie.content_rating, ...movie.genres]) {
    const item = document.createElement('li'); item.className = 'info'; item.textContent = tag; tags.append(item);
  }
  card.append(tags);
  const get = document.createElement('a'); get.className = 'get';
  get.href = `/movie.html?id=${encodeURIComponent(movie.id)}`;
  get.innerHTML = 'View details <span aria-hidden="true">↗</span>'; card.append(get);
  if (removable) {
    const remove = document.createElement('button'); remove.className = 'secondary-button';
    remove.textContent = 'Remove'; remove.type = 'button';
    remove.addEventListener('click', () => onRemove?.(movie)); card.append(remove);
  }
  return card;
}

function fillCards(container, movies, options) {
  container.replaceChildren(...movies.map(movie => movieCard(movie, options)));
}

function setStatus(message, id = 'status-message') {
  const element = document.getElementById(id);
  if (element) element.textContent = message;
}

function showResults(title, explanation, movies) {
  const panel = document.getElementById('results-panel');
  panel.hidden = false;
  document.getElementById('results-title').textContent = `${title} (${movies.length})`;
  document.getElementById('results-explanation').textContent =
    movies.length ? explanation : 'No matching movies in our catalog. Try another choice.';
  const grid = document.getElementById('results-grid');
  fillCards(grid, movies);
}

function showHomepageSections(visible) {
  for (const section of document.querySelectorAll('.movie-section')) section.hidden = !visible;
}

async function loadHomepage() {
  const params = new URLSearchParams(location.search);
  const selectedGenre = params.get('genre');
  const searchBox = document.querySelector('.search-input');
  const searchForm = document.getElementById('search-form');
  const recommendationForm = document.getElementById('recommend-form');
  const panel = document.getElementById('results-panel');

  try {
    const catalog = await request('/movies');
    for (const heading of document.querySelectorAll('.section-heading')) {
      const group = heading.closest('.movie-section')?.querySelector('.group');
      const container = group?.querySelector('.main-card');
      if (container) fillCards(container, catalog.filter(m => m.section === heading.textContent.trim()));
    }
    setStatus(`${catalog.length} movies ready to explore.`);
    document.querySelectorAll('.genre-pill').forEach(pill => {
      const genre = new URL(pill.getAttribute('href'), 'http://localhost').searchParams.get('genre');
      pill.classList.toggle('is-active', genre === selectedGenre);
      if (genre === selectedGenre) pill.setAttribute('aria-current', 'page');
    });
    if (selectedGenre) {
      const movies = await request(`/movies?genre=${encodeURIComponent(selectedGenre)}`);
      showHomepageSections(false);
      showResults(`${selectedGenre} movies`, `Filtered by the ${selectedGenre} genre.`, movies);
    }
  } catch (error) {
    setStatus(`Could not load the catalog: ${error.message}`);
  }

  searchForm?.addEventListener('submit', event => {
    event.preventDefault();
    document.getElementById('results-panel')?.scrollIntoView({behavior:'smooth', block:'start'});
  });
  document.addEventListener('keydown', event => {
    if (event.key === '/' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) {
      event.preventDefault(); searchBox?.focus();
    }
    if (event.key === 'Escape' && document.activeElement === searchBox) searchBox.blur();
  });
  let searchCount = 0;
  let timer;
  searchBox?.addEventListener('input', () => {
    clearTimeout(timer);
    const term = searchBox.value.trim();
    const seq = ++searchCount;
    if (!term) {
      if (selectedGenre) {
        showHomepageSections(false);
        request(`/movies?genre=${encodeURIComponent(selectedGenre)}`)
          .then(movies => { if (seq === searchCount) showResults(`${selectedGenre} movies`, 'Genre results', movies); })
          .catch(error => setStatus(error.message));
      } else {
        panel.hidden = true;
        showHomepageSections(true);
      }
      return;
    }
    timer = setTimeout(async () => {
      try {
        const query = `/movies?search=${encodeURIComponent(term)}` +
          (selectedGenre ? `&genre=${encodeURIComponent(selectedGenre)}` : '');
        const movies = await request(query);
        if (seq !== searchCount) return;
        showHomepageSections(false);
        showResults('Search results', `Matching “${term}”`, movies);
      } catch (error) { setStatus(error.message); }
    }, 200);
  });

  recommendationForm?.addEventListener('submit', async event => {
    event.preventDefault();
    const mood = document.getElementById('mood').value;
    const language = document.getElementById('language').value;
    if (!mood) { setStatus('Select your mood first.'); return; }
    try {
      setStatus('Finding movies for your mood…');
      const result = await request('/recommendations', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({mood, language: language || 'Any', limit: 12})
      });
      showHomepageSections(false);
      showResults('Your recommendations', `${result.explanation} Language: ${language || 'Any'}.`, result.movies);
      setStatus(`Found ${result.count} recommendation(s).`);
      panel.scrollIntoView({behavior:'smooth', block:'start'});
    } catch (error) { setStatus(`Recommendation error: ${error.message}`); }
  });
}

function appendText(tag, text, className = '') {
  const element = document.createElement(tag); element.textContent = text;
  if (className) element.className = className;
  return element;
}

async function loadMovieDetails() {
  const id = new URLSearchParams(location.search).get('id');
  const container = document.getElementById('movie-details');
  if (!id) { container.textContent = 'Choose a movie from the homepage.'; return; }
  try {
    const movie = await request(`/movies/${encodeURIComponent(id)}`);
    document.title = `${movie.title} — MOOD`;
    const info = appendText('section', '', 'info-card');
    const poster = document.createElement('img'); poster.src = movie.poster_url;
    poster.alt = `${movie.title} poster`; poster.addEventListener('error', () => { poster.style.display='none'; });
    info.append(poster);
    const detail = appendText('div','', 'Cover-detail');
    detail.append(appendText('h2', `${movie.title} (${movie.year})`));
    const tags = appendText('ul', '', 'info-li-pg');
    for (const item of [movie.content_rating, ...movie.genres]) {
      tags.append(appendText('li', item, 'info-pg'));
    }
    detail.append(tags, appendText('p', `Language: ${movie.language}`, 'language'));
    if (movie.imdb_rating !== null) detail.append(appendText('p', `IMDb rating: ${movie.imdb_rating}/10`, 'language'));
    if (movie.director) detail.append(appendText('p', `Directed by: ${movie.director}`, 'director-name'));
    const wishlist = appendText('button', '🍿 Add to Wishlist', 'wishlist');
    wishlist.type = 'button';
    const feedback = appendText('p', '', 'status-message');
    wishlist.addEventListener('click', async () => {
      try {
        const result = await request(`/wishlist/${encodeURIComponent(movie.id)}`, {
          method:'POST', headers:guestHeaders()
        });
        feedback.textContent = result.message;
      } catch (error) { feedback.textContent = error.message; }
    });
    detail.append(wishlist, feedback); info.append(detail);
    const story = appendText('section', '', 'summary');
    story.append(appendText('h2', 'The Story'), appendText('p', movie.overview || 'Synopsis coming soon.'));
    container.replaceChildren(info, story);
  } catch (error) { container.textContent = `Could not load movie: ${error.message}`; }
}

async function loadWishlist() {
  const grid = document.getElementById('wishlist-grid');
  const refresh = async () => {
    try {
      const movies = await request('/wishlist', {headers:guestHeaders()});
      fillCards(grid, movies, {
        removable:true,
        onRemove:async (movie) => {
          try {
            await request(`/wishlist/${encodeURIComponent(movie.id)}`,
              {method:'DELETE', headers:guestHeaders()});
            await refresh();
          } catch (error) { setStatus(error.message, 'wishlist-status'); }
        }
      });
      setStatus(movies.length ? `${movies.length} movie(s) saved.` : 'No saved movies yet. Open any movie and press Add to Wishlist.', 'wishlist-status');
    } catch (error) { setStatus(error.message, 'wishlist-status'); }
  };
  await refresh();
}

if (document.body.dataset.page === 'movie') loadMovieDetails();
else if (document.body.dataset.page === 'wishlist') loadWishlist();
else if (document.getElementById('recommend-form')) loadHomepage();

// A readable branded cover is visible even when third-party artwork cannot load.
document.querySelectorAll('.art-poster img').forEach(img => {
  const hideBrokenImage = () => { img.style.display = 'none'; };
  img.addEventListener('error', hideBrokenImage);
  if (img.complete && img.naturalWidth === 0) hideBrokenImage();
});
