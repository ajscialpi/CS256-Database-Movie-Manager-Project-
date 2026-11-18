"""MovieVault search and validated PostgreSQL CRUD workflows."""

import os
from pathlib import Path
import psycopg
from flask import (
    Flask, abort, flash, redirect, render_template, request, url_for,
)
from psycopg.errors import ForeignKeyViolation, UniqueViolation

from repository_postgres import (
    MovieNotFound, StaleMovie, create_movie, delete_movie, get_movie,
    get_movie_review_report, movie_version, search_movies, update_movie,
    update_movie_genres,
)
from validation import BULK_GENRES, FIELDS, validate_movie

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


# Home page with movie search
@app.get('/')
def home():
    # Get the search text from the URL
    query = request.args.get('q', '').strip()

    return _render_home(query)


def _render_home(query, message='', status=200):
    try:
        display_rows = search_movies(query)
    except (psycopg.Error, KeyError):
        display_rows = []
        message = (message + ' The movie list is temporarily unavailable. Please try again later.').strip()
        status = 503
    return render_template(
        'index.html', rows=display_rows, query=query,
        genres=BULK_GENRES, message=message,
    ), status


@app.post('/movies/genres')
def bulk_movie_genres():
    query = request.form.get('q', '').strip()
    versions = {
        key.removeprefix('version_'): value
        for key, value in request.form.items() if key.startswith('version_')
    }
    try:
        count = update_movie_genres(
            request.form.getlist('movie_ids'), request.form.get('genre', ''), versions,
        )
    except ValueError as error:
        message = str(error) + ' No genre changes were saved.'
        status = 400
    except MovieNotFound:
        message = ('A selected movie no longer exists. The transaction was rolled back; '
                   'no genre changes were saved. Review the current list and select again.')
        status = 409
    except StaleMovie:
        message = ('A selected movie changed after you opened the list. The transaction '
                   'was rolled back; no genre changes were saved. Review the current list and select again.')
        status = 409
    except (psycopg.IntegrityError, psycopg.DataError, RuntimeError):
        message = ('The selected movies could not all be updated. The transaction was '
                   'rolled back; no genre changes were saved. Review the current list and select again.')
        status = 409
    except (psycopg.Error, KeyError):
        # A lost connection during COMMIT can make its outcome uncertain.
        # Do not expose database details or claim a rollback we cannot confirm.
        message = ('The database could not confirm this update. Refresh and check the '
                   'selected movies before trying again.')
        status = 503
    else:
        flash(f'Updated the genre for all {count} selected movies.', 'success')
        return redirect(url_for('home', q=query) if query else url_for('home'), code=303)
    # Errors reach here only after the transaction and connection have exited.
    return _render_home(query, message, status)


@app.get('/reports/movie-reviews')
def movie_review_report():
    try:
        rows = get_movie_review_report()
    except (psycopg.Error, KeyError, OSError):
        # Do not expose connection settings or database exception messages.
        app.logger.warning('Movie review report unavailable.')
        return render_template(
            'movie_review_report.html', rows=[],
            error='The movie review report is temporarily unavailable. Please try again later.',
        ), 503
    return render_template('movie_review_report.html', rows=rows, error='')


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
    return render_template('movie_detail.html', movie=_movie_or_404(movie_id))


def _movie_or_404(movie_id):
    # PostgreSQL integer keys cannot exceed this range.
    if movie_id > 2147483647:
        abort(404)
    movie = get_movie(movie_id)
    if movie is None:
        abort(404)
    return movie


@app.route('/movies/<int:movie_id>/edit', methods=['GET', 'POST'])
def edit_movie(movie_id):
    movie = _movie_or_404(movie_id)
    values = movie.copy()
    errors = {}
    message = ''
    status = 200
    version = movie_version(movie)

    if request.method == 'POST':
        # The URL chooses the movie. Ignore any submitted replacement ID.
        values, errors = validate_movie({**request.form, 'movie_id': str(movie_id)})
        version = request.form.get('version', '')
        if errors:
            status = 400
        else:
            try:
                update_movie(movie_id, values, version)
            except MovieNotFound:
                abort(404)
            except StaleMovie:
                status = 409
                message = ('This movie changed after you opened the form. '
                           'Your changes were not saved. Open the latest movie before editing again.')
            except (psycopg.IntegrityError, psycopg.DataError):
                status = 400
                message = 'These values could not be saved. Check the movie details.'
            else:
                return redirect(url_for('movie_detail', movie_id=movie_id), code=303)

    return render_template(
        'edit_movie.html', movie=movie, fields=FIELDS[1:], values=values,
        errors=errors, version=version, message=message,
    ), status


@app.route('/movies/<int:movie_id>/delete', methods=['GET', 'POST'])
def confirm_delete_movie(movie_id):
    movie = _movie_or_404(movie_id)
    version = movie_version(movie)
    message = ''
    status = 200

    if request.method == 'POST':
        version = request.form.get('version', '')
        if request.form.get('confirm') != 'yes':
            message = 'Please confirm deletion using the Delete movie button.'
            status = 400
        else:
            try:
                delete_movie(movie_id, version)
            except MovieNotFound:
                abort(404)
            except StaleMovie:
                status = 409
                message = ('This movie changed after you opened the confirmation. '
                           'Nothing was deleted. Open the latest movie before trying again.')
            except ForeignKeyViolation:
                status = 409
                message = 'This movie has related records, such as reviews, and cannot be deleted.'
            else:
                return redirect(url_for('home'), code=303)

    return render_template(
        'delete_movie.html', movie=movie, version=version, message=message,
    ), status


if __name__ == '__main__':
    app.run(
        host='127.0.0.1',
        port=5001,
        debug=True
    )
