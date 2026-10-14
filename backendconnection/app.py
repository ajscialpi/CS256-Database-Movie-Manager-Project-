"""MovieVault Flask application - Lesson 5."""

import os
import getpass
import psycopg
from psycopg.rows import dict_row
from flask import Flask, render_template

app = Flask(
    __name__,
    template_folder='../templates',
    static_folder='../templates',
    static_url_path='/templates',
)

app.config['SECRET_KEY'] = os.getenv(
    'PROJECT_SECRET_KEY', 'local-practice-only'
)


# Read movie records from PostgreSQL
def read_m05_rows():
    with psycopg.connect(
        os.environ['DATABASE_DSN'],
        row_factory=dict_row
    ) as conn:
        return conn.execute("""
            SELECT movie_id, title, genre AS category,
                   release_year, director,
                   content_rating, synopsis
            FROM cs256_m05_movievault.movies
            WHERE title ILIKE %s
            ORDER BY movie_id
        """, ('%Sample%',)).fetchall()


# Home page
@app.get('/')
def home():
    display_rows = read_m05_rows()
    return render_template('index.html', rows=display_rows)


if __name__ == '__main__':
    app.run(
        host='127.0.0.1',
        port=5001,
        debug=True
    )
