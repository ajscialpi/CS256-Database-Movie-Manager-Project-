"""Local report tests use mocks; verify_m09_server.py checks PostgreSQL."""
from decimal import Decimal
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backendconnection'))

import app as web
import repository_postgres as repository
import psycopg


class ReportTests(unittest.TestCase):
    def setUp(self):
        web.app.testing = True
        self.client = web.app.test_client()

    @patch.object(web, 'get_movie_review_report')
    def test_table_ratings_links_and_escaping(self, report):
        report.return_value = [{
            'movie_id': 1, 'title': '<Movie>', 'genre': 'Drama',
            'release_year': 2026, 'total_reviews': 3,
            'average_rating': Decimal('7.33'),
        }]
        response = self.client.get('/reports/movie-reviews')
        self.assertEqual(response.status_code, 200)
        for heading in ('Movie', 'Genre', 'Release Year', 'Total Reviews', 'Average Rating (out of 10)'):
            self.assertIn(f'<th scope="col">{heading}</th>', response.text)
        for text in ('&lt;Movie&gt;', 'Drama', '2026', '>3</td>', '>7.33</td>', 'href="/movies/1"'):
            self.assertIn(text, response.text)
        self.assertNotIn('<Movie>', response.text)
        self.assertIn('tabindex="0"', response.text)
        report.assert_called_once_with()

    @patch.object(web, 'get_movie_review_report')
    def test_missing_average_differs_from_zero_rating(self, report):
        for count, average, display in ((0, None, 'N/A'), (1, Decimal('0'), '0.00')):
            with self.subTest(average=average):
                report.return_value = [{
                    'movie_id': 1, 'title': 'Example', 'genre': 'Drama',
                    'release_year': 2026, 'total_reviews': count, 'average_rating': average,
                }]
                response = self.client.get('/reports/movie-reviews')
                self.assertEqual(response.status_code, 200)
                self.assertIn(f'>{count}</td>', response.text)
                self.assertIn(f'>{display}</td>', response.text)

    @patch.object(web, 'get_movie_review_report', return_value=[])
    def test_empty_database(self, report):
        response = self.client.get('/reports/movie-reviews')
        self.assertEqual(response.status_code, 200)
        self.assertIn('No movies are available yet.', response.text)
        self.assertNotIn('<table', response.text)

    def test_errors_do_not_expose_configuration_or_look_like_empty_results(self):
        for error in (psycopg.OperationalError('private connection detail'),
                      KeyError('DATABASE_DSN'), FileNotFoundError('private path')):
            with self.subTest(error=type(error).__name__), patch.object(
                web, 'get_movie_review_report', side_effect=error,
            ), self.assertLogs(web.app.logger, level='WARNING') as logs:
                response = self.client.get('/reports/movie-reviews')
            self.assertEqual(response.status_code, 503)
            self.assertIn('temporarily unavailable', response.text)
            self.assertNotIn('No movies are available', response.text)
            for secret in ('private connection detail', 'DATABASE_DSN', 'private path'):
                self.assertNotIn(secret, response.text + ''.join(logs.output))

    @patch.object(web, 'search_movies', return_value=[])
    def test_home_navigation(self, search):
        self.assertIn('href="/reports/movie-reviews"', self.client.get('/').text)

    @patch.dict(os.environ, {'DATABASE_DSN': 'mock-only'})
    @patch.object(repository.psycopg, 'connect')
    def test_repository_executes_shared_sql(self, connect):
        conn = connect.return_value.__enter__.return_value
        conn.execute.return_value.fetchall.return_value = [{'movie_id': 1}]
        self.assertEqual(repository.get_movie_review_report(), [{'movie_id': 1}])
        conn.execute.assert_called_once_with(repository.movie_review_report_sql())

    def test_flat_server_layout_loads_sql(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            for filename in ('validation.py', 'repository_postgres.py'):
                shutil.copy2(root / 'backendconnection' / filename, destination)
            shutil.copytree(root / 'sql', destination / 'sql')
            result = subprocess.run(
                [sys.executable, '-B', '-c',
                 'from repository_postgres import movie_review_report_sql; '
                 'assert "COUNT(r.review_id)" in movie_review_report_sql()'],
                cwd=directory, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
