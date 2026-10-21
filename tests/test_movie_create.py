"""Local checks with mocked database calls; no PostgreSQL rows are written."""
import os
from pathlib import Path
import sys
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backendconnection'))

import app as web
import repository_postgres as repository
from psycopg.errors import UniqueViolation
from validation import validate_movie


VALID = {
    'movie_id': '9001',
    'title': 'Sample Film: Midnight Library',
    'genre': 'Mystery',
    'release_year': '2026',
    'director': 'Jordan Example',
    'content_rating': 'PG',
    'synopsis': 'A fictional librarian discovers a hidden room full of clues.',
}


class MovieFlowTests(unittest.TestCase):
    def setUp(self):
        web.app.config['TESTING'] = True
        self.client = web.app.test_client()

    def test_form_has_all_named_fields_and_stylesheet(self):
        response = self.client.get('/movies/new')
        self.assertEqual(response.status_code, 200)
        for field in VALID:
            self.assertIn(f'name="{field}"', response.text)
        with self.client.get('/templates/brand.css') as stylesheet:
            self.assertEqual(stylesheet.status_code, 200)

    @patch.object(web, 'create_movie')
    def test_invalid_input_never_calls_insert(self, create):
        cases = [
            ('synopsis', 'Short'), ('synopsis', 'x' * 1001),
            ('title', '   '), ('release_year', '1887'),
            ('release_year', '2101'), ('release_year', '2026.5'),
            ('movie_id', '0'), ('movie_id', '2147483648'),
            ('movie_id', 'abc'),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                response = self.client.post('/movies/new', data={**VALID, field: value})
                self.assertEqual(response.status_code, 400)
                self.assertIn('Movie not saved', response.text)
                self.assertIn(VALID['director'], response.text)
        response = self.client.post('/movies/new', data={})
        self.assertEqual(response.status_code, 400)
        create.assert_not_called()

    @patch.object(web, 'get_movie')
    @patch.object(web, 'create_movie', return_value=9001)
    def test_save_redirect_and_refresh_only_read(self, create, get):
        cleaned, _ = validate_movie(VALID)
        get.return_value = cleaned
        response = self.client.post('/movies/new', data=VALID)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers['Location'], '/movies/9001')
        create.assert_called_once_with(cleaned)
        for _ in range(2):
            detail = self.client.get(response.headers['Location'])
            self.assertEqual(detail.status_code, 200)
            self.assertIn(VALID['synopsis'], detail.text)
        create.assert_called_once()
        self.assertEqual(get.call_count, 2)
        get.assert_called_with(9001)

    @patch.object(web, 'create_movie', side_effect=UniqueViolation('duplicate'))
    def test_duplicate_id_returns_field_error(self, create):
        response = self.client.post('/movies/new', data=VALID)
        self.assertEqual(response.status_code, 400)
        self.assertIn('That movie ID already exists', response.text)

    @patch.object(web, 'get_movie', return_value=None)
    def test_unknown_and_oversized_ids_return_404(self, get):
        self.assertEqual(self.client.get('/movies/9002').status_code, 404)
        self.assertEqual(self.client.get('/movies/2147483648').status_code, 404)
        get.assert_called_once_with(9002)

    @patch.object(web, 'read_m05_rows')
    def test_home_links_to_create_and_saved_movie(self, read):
        read.return_value = [{'movie_id': 9001, 'title': 'New Movie', 'category': 'Mystery'}]
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('href="/movies/new"', response.text)
        self.assertIn('href="/movies/9001"', response.text)

    def test_validation_trims_and_accepts_year_boundaries(self):
        for year in ('1888', '2100'):
            values, errors = validate_movie({**VALID, 'title': '  Movie  ', 'release_year': year})
            self.assertEqual(errors, {})
            self.assertEqual(values['title'], 'Movie')
            self.assertEqual(values['release_year'], int(year))

    @patch.object(web, 'get_movie')
    def test_saved_text_is_html_escaped(self, get):
        get.return_value = {**VALID, 'title': '<script>alert(1)</script>'}
        response = self.client.get('/movies/9001')
        self.assertNotIn('<script>', response.text)
        self.assertIn('&lt;script&gt;', response.text)

    def test_flat_server_layout_finds_templates(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            for filename in ('app.py', 'validation.py', 'repository_postgres.py'):
                shutil.copy2(root / 'backendconnection' / filename, destination)
            shutil.copytree(root / 'templates', destination / 'templates')
            result = subprocess.run(
                [sys.executable, '-B', '-c',
                 "import app; app.app.testing = True; "
                 "response = app.app.test_client().get('/movies/new'); "
                 "assert response.status_code == 200; "
                 "assert b'name=\"synopsis\"' in response.data"],
                cwd=directory, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


class RepositoryTests(unittest.TestCase):
    @patch.dict(os.environ, {'DATABASE_DSN': 'mock-only'})
    @patch.object(repository.psycopg, 'connect')
    def test_insert_binds_values_separately_and_commits(self, connect):
        conn = connect.return_value.__enter__.return_value
        conn.execute.return_value.fetchone.return_value = (9001,)
        values, _ = validate_movie({**VALID, 'title': "O'Brien's Movie"})
        self.assertEqual(repository.create_movie(values), 9001)
        sql, parameters = conn.execute.call_args.args
        self.assertIn('INSERT INTO cs256_m05_movievault.movies', sql)
        self.assertEqual(sql.count('%s'), 7)
        self.assertNotIn(values['title'], sql)
        self.assertEqual(parameters, (9001, "O'Brien's Movie", 'Mystery', 2026,
                                      'Jordan Example', 'PG', VALID['synopsis']))
        conn.commit.assert_called_once()

    @patch.dict(os.environ, {'DATABASE_DSN': 'mock-only'})
    @patch.object(repository.psycopg, 'connect')
    def test_detail_query_binds_primary_key(self, connect):
        conn = connect.return_value.__enter__.return_value
        conn.execute.return_value.fetchone.return_value = VALID
        self.assertEqual(repository.get_movie(9001), VALID)
        sql, parameters = conn.execute.call_args.args
        self.assertIn('WHERE movie_id = %s', sql)
        self.assertEqual(parameters, (9001,))


if __name__ == '__main__':
    unittest.main()
