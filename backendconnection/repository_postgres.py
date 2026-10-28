import os

import psycopg
from psycopg.rows import dict_row


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
