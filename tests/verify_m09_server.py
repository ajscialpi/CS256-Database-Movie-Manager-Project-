"""Read-only PostgreSQL checks. Prints evidence for one existing movie only.

Repository: python -B tests/verify_m09_server.py
Flat King's layout: python -B verify_m09_server.py
Requires DATABASE_DSN. No INSERT, UPDATE, DELETE, or schema changes.
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import json
import os
from pathlib import Path
import re
import sys

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parent
if (ROOT.parent / 'backendconnection').is_dir():
    sys.path.insert(0, str(ROOT.parent / 'backendconnection'))

from app import app
from repository_postgres import movie_review_report_sql


def check_fixture_sql(conn):
    # CTEs exist only for this SELECT; no test records are saved.
    query = movie_review_report_sql().replace(
        'cs256_m05_movievault.movies', 'fixture_movies',
    ).replace('cs256_m05_movievault.reviews', 'fixture_reviews')
    rows = conn.execute('''
        WITH fixture_movies(movie_id, title, genre, release_year) AS (
            VALUES (1, 'Same title', 'Drama', 2026),
                   (2, 'Same title', 'Drama', 2026),
                   (3, 'No reviews', 'Comedy', 2025),
                   (4, 'Same title', 'Drama', 2026)
        ), fixture_reviews(review_id, movie_id, rating) AS (
            VALUES (11, 1, 8.0::numeric), (12, 1, 8.0::numeric),
                   (13, 1, 6.0::numeric), (14, 2, 0.0::numeric),
                   (15, 4, 5.0::numeric)
        )
    ''' + query).fetchall()
    assert [row['movie_id'] for row in rows] == [1, 2, 4, 3]
    assert [(row['total_reviews'], row['average_rating']) for row in rows] == [
        (3, Decimal('7.33')), (1, Decimal('0.00')),
        (1, Decimal('5.00')), (0, None),
    ]
    return 'PASS: repeated ratings, same-title movies, rounding, zero rating, no reviews, tie order'


def main():
    evidence = {'verified_at_utc': datetime.now(timezone.utc).isoformat(),
                'method': 'Read-only PostgreSQL queries and Flask test client; no database mocks.'}
    with psycopg.connect(os.environ['DATABASE_DSN'], row_factory=dict_row) as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        evidence['synthetic_sql_checks'] = check_fixture_sql(conn)
        rows = conn.execute(movie_review_report_sql()).fetchall()
        movie_count = conn.execute('SELECT COUNT(*) AS n FROM cs256_m05_movievault.movies').fetchone()['n']
        assert len(rows) == movie_count == len({row['movie_id'] for row in rows})
        evidence['one_row_per_movie'] = True
        if rows:
            # Prefer a reviewed movie, using the report's review-count ordering.
            selected = rows[0]
            reviews = conn.execute('''
                SELECT review_id, rating FROM cs256_m05_movievault.reviews
                WHERE movie_id = %s ORDER BY review_id
            ''', (selected['movie_id'],)).fetchall()
            total = sum((review['rating'] for review in reviews), Decimal('0'))
            average = (total / len(reviews)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if reviews else None
            assert selected['total_reviews'] == len(reviews)
            assert selected['average_rating'] == average
            evidence['independent_check'] = {
                'movie_id': selected['movie_id'], 'title': selected['title'],
                'reviews': reviews, 'rating_sum': total, 'count': len(reviews),
                'calculated_average': average, 'report_count': selected['total_reviews'],
                'report_average': selected['average_rating'], 'matches': True,
            }
        else:
            evidence['independent_check'] = 'NOT RUN: no movies exist.'

    # All connections opened by the real route use PostgreSQL read-only mode.
    # Preserve any configured connection options, including connection routing.
    from psycopg.conninfo import conninfo_to_dict, make_conninfo
    settings = conninfo_to_dict(os.environ['DATABASE_DSN'])
    options = settings.get('options', '') + ' -c default_transaction_read_only=on'
    os.environ['DATABASE_DSN'] = make_conninfo(os.environ['DATABASE_DSN'], options=options)
    app.testing = True
    client = app.test_client()
    response = client.get('/reports/movie-reviews')
    assert response.status_code == 200
    if rows:
        for heading in ('Movie', 'Genre', 'Release Year', 'Total Reviews', 'Average Rating (out of 10)'):
            assert f'<th scope="col">{heading}</th>' in response.text
        assert f'href="/movies/{rows[0]["movie_id"]}"' in response.text
        selected_html = next(
            row for row in re.findall(r'<tr>(.*?)</tr>', response.text, re.S)
            if f'href="/movies/{rows[0]["movie_id"]}"' in row
        )
        cells = re.findall(r'<td[^>]*>(.*?)</td>', selected_html, re.S)
        assert cells[-2] == str(rows[0]['total_reviews'])
        expected_average = f'{rows[0]["average_rating"]:.2f}' if rows[0]['average_rating'] is not None else 'N/A'
        assert cells[-1] == expected_average
        assert client.get(f'/movies/{rows[0]["movie_id"]}').status_code == 200
    else:
        assert 'No movies are available yet.' in response.text
    assert client.get('/').status_code == 200
    assert client.get('/movies/new').status_code == 200
    evidence['report_home_create_form_and_existing_detail_gets'] = 'PASS (detail only if a movie exists)'
    evidence['selected_movie_html_matches_sql'] = bool(rows)
    evidence['result'] = 'PASS'
    print(json.dumps(evidence, indent=2, default=str))


if __name__ == '__main__':
    try:
        main()
    except (psycopg.Error, KeyError, OSError):
        sys.exit('Verification unavailable: check database access and uploaded files. Connection details omitted.')
