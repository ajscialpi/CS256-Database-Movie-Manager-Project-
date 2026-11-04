"""Run with DATABASE_DSN against King's PostgreSQL; modifies only owned test rows.

From the repository: python tests/verify_m08_server.py
From the flat King's layout: python verify_m08_server.py
Prints JSON evidence only after every assertion and cleanup succeeds.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import sys
import uuid

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parent
if (ROOT.parent / 'backendconnection').is_dir():
    sys.path.insert(0, str(ROOT.parent / 'backendconnection'))

from app import app


def query(sql, params=()):
    with psycopg.connect(os.environ['DATABASE_DSN'], row_factory=dict_row) as conn:
        return conn.execute(sql, params).fetchall()


def snapshot():
    return {
        'movies': query('SELECT * FROM cs256_m05_movievault.movies ORDER BY movie_id'),
        'reviews': query('SELECT * FROM cs256_m05_movievault.reviews ORDER BY review_id'),
    }


def movie(movie_id):
    rows = query('SELECT * FROM cs256_m05_movievault.movies WHERE movie_id = %s', (movie_id,))
    return rows[0] if rows else None


def token(response):
    assert response.status_code == 200
    match = re.search(r'name="version" value="([a-f0-9]{64})"', response.text)
    assert match, 'Form must contain the original fingerprint.'
    return match.group(1)


def main():
    app.testing = True
    client = app.test_client()
    before = snapshot()
    # Random IDs are checked before creation; never repurpose an existing row.
    movie_id = secrets.randbelow(900000000) + 1000000000
    review_id = secrets.randbelow(900000000) + 1000000000
    assert movie(movie_id) is None
    assert not query('SELECT review_id FROM cs256_m05_movievault.reviews WHERE review_id = %s', (review_id,))
    marker = uuid.uuid4().hex[:12]
    title = f'M08 Disposable {marker}'
    review_text = f'M08 disposable review {marker}'
    form = {
        'movie_id': str(movie_id), 'title': title, 'genre': 'Mystery',
        'release_year': '2026', 'director': 'Jordan Example', 'content_rating': 'PG',
        'synopsis': 'A fictional movie created only to verify the M08 CRUD workflow.',
    }
    evidence = {
        'verified_at_utc': datetime.now(timezone.utc).isoformat(),
        'method': "Flask test client on King's with real PostgreSQL; no database mocks. Cancel follows the form's link; two form GETs simulate browser tabs.",
        'movie_id': movie_id,
        'existing_movie_count_before': len(before['movies']),
    }
    created = False
    review_created = False
    try:
        response = client.post('/movies/new', data=form)
        assert response.status_code == 303
        created = True
        path = f'/movies/{movie_id}'
        assert response.location == path
        original = movie(movie_id)
        assert original is not None and original['title'] == title
        evidence['create'] = {'http_status': response.status_code, 'saved_movie': original}

        tab_a = client.get(path + '/edit')
        tab_b = client.get(path + '/edit')
        old_delete = client.get(path + '/delete')
        old_version = token(tab_a)
        assert token(tab_b) == old_version == token(old_delete)
        updated_form = {**form, 'title': title + " - O'Brien Edit", 'genre': 'Drama',
                        'release_year': '2025', 'director': 'Casey Example',
                        'content_rating': 'PG-13',
                        'synopsis': 'The updated fictional movie follows a director solving a theater mystery.',
                        'movie_id': '1', 'version': old_version}
        response = client.post(path + '/edit', data=updated_form)
        assert response.status_code == 303 and response.location == path
        updated = movie(movie_id)
        assert updated['movie_id'] == original['movie_id']
        for field in form.keys() - {'movie_id'}:
            expected = int(updated_form[field]) if field == 'release_year' else updated_form[field]
            assert updated[field] == expected
        evidence['update'] = {'http_status': response.status_code, 'before': original, 'after': updated}

        response = client.post(path + '/edit', data={**form, 'version': token(tab_b)})
        assert response.status_code == 409 and movie(movie_id) == updated
        evidence['stale_edit'] = {'http_status': response.status_code, 'after': movie(movie_id)}
        response = client.post(path + '/delete', data={'confirm': 'yes', 'version': token(old_delete)})
        assert response.status_code == 409 and movie(movie_id) == updated
        evidence['stale_delete'] = {'http_status': response.status_code, 'after': movie(movie_id)}

        fresh = client.get(path + '/edit')
        response = client.post(path + '/edit', data={**updated_form, 'synopsis': 'Short', 'version': token(fresh)})
        assert response.status_code == 400 and movie(movie_id) == updated
        evidence['invalid_edit'] = {'http_status': response.status_code, 'unchanged': True}
        for action, data in (('edit', updated_form), ('delete', {'confirm': 'yes'})):
            data = {key: value for key, value in data.items() if key != 'version'}
            response = client.post(path + '/' + action, data=data)
            assert response.status_code == 409 and movie(movie_id) == updated
        evidence['missing_versions'] = {'edit_status': 409, 'delete_status': 409, 'unchanged': True}

        confirmation = client.get(path + '/delete')
        assert confirmation.status_code == 200 and str(movie_id) in confirmation.text
        cancel = re.search(r'href="([^"]+)">Cancel</a>', confirmation.text)
        assert cancel and cancel.group(1) == path
        response = client.get(cancel.group(1))
        assert response.status_code == 200 and movie(movie_id) == updated
        evidence['cancel'] = {'confirmation_status': confirmation.status_code,
                              'cancel_get_status': response.status_code,
                              'before': updated, 'after': movie(movie_id)}
        response = client.post(path + '/delete', data={'version': token(confirmation)})
        assert response.status_code == 400 and movie(movie_id) == updated
        evidence['unconfirmed_delete'] = {'http_status': response.status_code, 'unchanged': True}

        # Verify the actual foreign key using a review belonging only to our movie.
        with psycopg.connect(os.environ['DATABASE_DSN']) as conn:
            conn.execute('''INSERT INTO cs256_m05_movievault.reviews
                (review_id, movie_id, display_name, rating, review_title, review_text)
                VALUES (%s, %s, %s, %s, %s, %s)''',
                (review_id, movie_id, 'M08 Test', 5, 'Disposable review', review_text))
        review_created = True
        response = client.post(path + '/delete', data={'confirm': 'yes', 'version': token(confirmation)})
        assert response.status_code == 409 and 'related records' in response.text
        assert movie(movie_id) == updated
        assert query('SELECT review_id FROM cs256_m05_movievault.reviews WHERE review_id = %s', (review_id,))
        evidence['foreign_key_restriction'] = {'http_status': response.status_code, 'movie_and_review_preserved': True}
        with psycopg.connect(os.environ['DATABASE_DSN']) as conn:
            result = conn.execute('DELETE FROM cs256_m05_movievault.reviews WHERE review_id = %s AND movie_id = %s AND review_text = %s',
                                  (review_id, movie_id, review_text))
            assert result.rowcount == 1
        review_created = False

        checks = []
        for search in (marker, 'NO-SUCH-MOVIE-' + marker, '', "O'Brien"):
            response = client.get('/', query_string={'q': search})
            assert response.status_code == 200
            if search == 'NO-SUCH-MOVIE-' + marker:
                assert 'No matching records yet.' in response.text
            else:
                assert path in response.text
            checks.append({'query': search, 'http_status': response.status_code})
        for _ in range(2):
            assert client.get(path).status_code == 200
        assert movie(movie_id) == updated
        evidence['search_and_detail'] = {'searches': checks, 'repeated_detail_statuses': [200, 200], 'unchanged': True}

        response = client.post(path + '/delete', data={'confirm': 'yes', 'version': token(client.get(path + '/delete'))})
        assert response.status_code == 303 and response.location == '/'
        assert movie(movie_id) is None
        evidence['delete'] = {'http_status': response.status_code, 'before': updated, 'after': None, 'rows_after': 0}
        created = False
        statuses = {}
        for action in ('edit', 'delete'):
            for method in ('GET', 'POST'):
                response = client.open(path + '/' + action, method=method, data={'confirm': 'yes', **updated_form})
                assert response.status_code == 404
                statuses[f'{method} {action}'] = response.status_code
        evidence['nonexistent_movie'] = statuses
    finally:
        # On failure, clean up only rows this run successfully created and owns.
        with psycopg.connect(os.environ['DATABASE_DSN']) as conn:
            if review_created:
                conn.execute('DELETE FROM cs256_m05_movievault.reviews WHERE review_id = %s AND movie_id = %s AND review_text = %s',
                             (review_id, movie_id, review_text))
            if created:
                conn.execute('DELETE FROM cs256_m05_movievault.movies WHERE movie_id = %s AND title IN (%s, %s)',
                             (movie_id, title, title + " - O'Brien Edit"))
    after = snapshot()
    assert after == before, 'Existing movie/review contents differ from the initial snapshot.'
    evidence['cleanup'] = {'existing_movie_count_after': len(after['movies']),
                           'all_existing_movies_and_reviews_unchanged': True,
                           'disposable_movie_and_review_removed': True}
    evidence['result'] = 'PASS'
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
