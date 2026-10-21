"""Run from the King's project folder using its Python environment.

Checks the uploaded Flask app against the real database. Sends only invalid
POSTs and reads the existing saved movie; it does not create a valid movie.
"""
import json
import os
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row

from app import app

app.config['TESTING'] = True
client = app.test_client()


def snapshot():
    with psycopg.connect(os.environ['DATABASE_DSN'], row_factory=dict_row) as conn:
        return {
            'count': conn.execute(
                'SELECT COUNT(*) AS count FROM cs256_m05_movievault.movies'
            ).fetchone()['count'],
            'saved_movie': conn.execute(
                'SELECT * FROM cs256_m05_movievault.movies WHERE movie_id = %s',
                (9001,),
            ).fetchone(),
            'rejected_id_rows': conn.execute(
                'SELECT COUNT(*) AS count FROM cs256_m05_movievault.movies WHERE movie_id = %s',
                (9002,),
            ).fetchone()['count'],
        }


def request(path, data=None):
    response = client.get(path) if data is None else client.post(path, data=data)
    with response:
        return response.status_code, response.get_data(as_text=True)


def main():
    before = snapshot()
    assert before['saved_movie'] is not None, 'Expected movie 9001 to exist.'
    assert before['rejected_id_rows'] == 0, 'ID 9002 must be unused for this check.'

    blank_status, blank_page = request('/movies/new', {'movie_id': '9002'})
    assert blank_status == 400 and 'This field is required.' in blank_page
    after_blank = snapshot()
    assert after_blank == before, 'Database changed during rejected required-field test.'

    short_form = {key: str(value) for key, value in before['saved_movie'].items()}
    short_form.update(movie_id='9002', synopsis='Short')
    short_status, short_page = request('/movies/new', short_form)
    assert short_status == 400 and 'Enter between 20 and 1,000 characters.' in short_page
    after_short = snapshot()
    assert after_short == before, 'Database changed during rejected synopsis test.'

    get_statuses = []
    for _ in range(2):
        status, page = request('/movies/9001')
        assert status == 200 and before['saved_movie']['title'] in page
        get_statuses.append(status)
    after_refresh = snapshot()
    assert after_refresh == before, 'Database changed during repeated detail GET requests.'

    print(json.dumps({
        'verified_at_utc': datetime.now(timezone.utc).isoformat(),
        'method': 'Flask test client on uploaded Kings app with real PostgreSQL; no database mocks. Repeated GETs simulate refresh, not a manual browser check.',
        'before': before,
        'required_fields_rejection': {'http_status': blank_status, 'after': after_blank},
        'short_synopsis_rejection': {'http_status': short_status, 'after': after_short},
        'repeated_detail_get': {'http_statuses': get_statuses, 'after': after_refresh},
        'result': 'PASS',
    }, indent=2))


if __name__ == '__main__':
    main()
