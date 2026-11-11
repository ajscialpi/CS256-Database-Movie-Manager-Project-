import hashlib
import json
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from validation import FIELDS


def movie_review_report_sql():
    """Use the same SQL in the repository and the flat King's upload layout."""
    directory = Path(__file__).resolve().parent
    if directory.name == 'backendconnection':
        directory = directory.parent
    return (directory / 'sql' / 'm09_movie_review_report.sql').read_text(encoding='utf-8')


def get_movie_review_report():
    with psycopg.connect(os.environ['DATABASE_DSN'], row_factory=dict_row) as conn:
        return conn.execute(movie_review_report_sql()).fetchall()


class MovieNotFound(Exception):
    """The selected movie no longer exists."""


class StaleMovie(Exception):
    """The movie changed after this form was opened."""


def movie_version(movie):
    """Fingerprint the stored fields, including the immutable movie ID."""
    payload = json.dumps([movie[field] for field in FIELDS], ensure_ascii=True)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def _lock_current_movie(conn, movie_id, version):
    # Keep the lock until the UPDATE/DELETE commits so another writer cannot
    # change the row between comparing the fingerprint and saving the change.
    movie = conn.execute(
        """
        SELECT movie_id, title, genre, release_year,
               director, content_rating, synopsis
        FROM cs256_m05_movievault.movies
        WHERE movie_id = %s
        FOR UPDATE
        """,
        (movie_id,),
    ).fetchone()
    if movie is None:
        raise MovieNotFound()
    if not version or version != movie_version(movie):
        raise StaleMovie()


def _require_one_row(cursor, movie_id):
    row = cursor.fetchone()
    if cursor.rowcount != 1 or row is None or row['movie_id'] != movie_id:
        # Raising inside the connection block rolls back an unexpected result.
        raise RuntimeError('Expected exactly one matching movie to change.')


def update_movie(movie_id, values, version):
    with psycopg.connect(os.environ['DATABASE_DSN'], row_factory=dict_row) as conn:
        _lock_current_movie(conn, movie_id, version)
        cursor = conn.execute(
            """
            UPDATE cs256_m05_movievault.movies
            SET title = %s, genre = %s, release_year = %s,
                director = %s, content_rating = %s, synopsis = %s
            WHERE movie_id = %s
            RETURNING movie_id
            """,
            (values['title'], values['genre'], values['release_year'],
             values['director'], values['content_rating'], values['synopsis'],
             movie_id),
        )
        _require_one_row(cursor, movie_id)
        # The connection context commits on success and rolls back on errors.


def delete_movie(movie_id, version):
    with psycopg.connect(os.environ['DATABASE_DSN'], row_factory=dict_row) as conn:
        _lock_current_movie(conn, movie_id, version)
        cursor = conn.execute(
            """
            DELETE FROM cs256_m05_movievault.movies
            WHERE movie_id = %s
            RETURNING movie_id
            """,
            (movie_id,),
        )
        _require_one_row(cursor, movie_id)


def create_movie(values):
    with psycopg.connect(os.environ["DATABASE_DSN"]) as conn:
        row = conn.execute(
            """
            INSERT INTO cs256_m05_movievault.movies
                (movie_id, title, genre, release_year,
                 director, content_rating, synopsis)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING movie_id
            """,
            (
                values["movie_id"],
                values["title"],
                values["genre"],
                values["release_year"],
                values["director"],
                values["content_rating"],
                values["synopsis"],
            ),
        ).fetchone()
        conn.commit()
        return row[0]


def get_movie(movie_id):
    with psycopg.connect(
        os.environ["DATABASE_DSN"],
        row_factory=dict_row,
    ) as conn:
        return conn.execute(
            """
            SELECT movie_id, title, genre, release_year,
                   director, content_rating, synopsis
            FROM cs256_m05_movievault.movies
            WHERE movie_id = %s
            """,
            (movie_id,),
        ).fetchone()

    
def search_movies(query):
    # Remove extra spaces from the search input
    query = query.strip()

    # Allow partial title matches
    pattern = f"%{query}%"

    with psycopg.connect(
        os.environ["DATABASE_DSN"],
        row_factory=dict_row,
    ) as conn:
        return conn.execute(
            """
            SELECT movie_id, title,
                   genre AS category,
                   release_year, director,
                   content_rating, synopsis
            FROM cs256_m05_movievault.movies
            WHERE title ILIKE %s
            ORDER BY title ASC, movie_id ASC
            LIMIT 25
            """,
            (pattern,),
        ).fetchall()
