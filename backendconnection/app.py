"""MovieVault PostgreSQL reads and validated movie creation."""

import os
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
from flask import (
    Flask, abort, redirect, render_template, request, url_for,
)
from psycopg.errors import UniqueViolation

from repository_postgres import create_movie, get_movie, search_movies
from validation import FIELDS, validate_movie

# Support both backendconnection/app.py locally and app.py on King's.
APP_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = APP_DIR / 'templates'
if not TEMPLATE_DIR.is_dir():
    TEMPLATE_DIR = APP_DIR.parent / 'templates'

app = Flask(
    __name__,
    template_folder=str(TEMPLATE_DIR),
    static_folder=str(TEMPLATE_DIR),
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
        """, ('%',)).fetchall()

# Home page with movie search
@app.get('/')
def home():
    # Get the search text from the URL
    query = request.args.get('q', '').strip()

    # Search PostgreSQL for matching movies
    display_rows = search_movies(query)

    # Display the results on the homepage
    return render_template(
        'index.html',
        rows=display_rows,
        query=query
    )



@app.route('/movies/new', methods=['GET', 'POST'])
def add_movie():
    values = {field: '' for field in FIELDS}
    errors = {}

    if request.method == 'POST':
        values, errors = validate_movie(request.form)
        if not errors:
            try:
                movie_id = create_movie(values)
            except UniqueViolation:
                errors['movie_id'] = (
                    'That movie ID already exists. Choose another ID.'
                )
            else:
                # Post/Redirect/Get: refreshing the detail page only reads.
                return redirect(
                    url_for('movie_detail', movie_id=movie_id), code=303
                )

    return render_template(
        'add_movie.html', fields=FIELDS, values=values, errors=errors
    ), (400 if errors else 200)


@app.get('/movies/<int:movie_id>')
def movie_detail(movie_id):
    # PostgreSQL integer keys cannot exceed this range.
    if movie_id > 2147483647:
        abort(404)
    movie = get_movie(movie_id)
    if movie is None:
        abort(404)
    return render_template('movie_detail.html', movie=movie)


if __name__ == '__main__':
    app.run(
        host='127.0.0.1',
        port=5001,
        debug=True
    )
