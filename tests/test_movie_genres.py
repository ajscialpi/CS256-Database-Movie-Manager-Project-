"""Bulk-update unit tests use mocks, not PostgreSQL rollback evidence."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backendconnection'))

import app as web
import repository_postgres as repository
import psycopg
from werkzeug.datastructures import MultiDict
from validation import validate_movie, validate_movie_genres
from test_movie_create import VALID


FIRST, _ = validate_movie(VALID)
SECOND = {**FIRST, 'movie_id': FIRST['movie_id'] + 1, 'title': 'Second test movie'}
VERSIONS = {str(movie['movie_id']): repository.movie_version(movie)
            for movie in (FIRST, SECOND)}
IDS = list(VERSIONS)


def result(row, count=1):
    cursor = MagicMock()
    cursor.fetchone.return_value = row
    cursor.rowcount = count
    return cursor


class GenreValidationTests(unittest.TestCase):
    def test_ids_are_sorted_and_genre_trimmed(self):
        self.assertEqual(validate_movie_genres(IDS[::-1], ' Drama ', VERSIONS),
                         ([FIRST['movie_id'], SECOND['movie_id']], 'Drama'))

    @patch.object(repository.psycopg, 'connect')
    def test_bad_requests_never_open_a_connection(self, connect):
        cases = [([], 'Drama', VERSIONS), (IDS * 13, 'Drama', VERSIONS),
                 ([IDS[0], IDS[0]], 'Drama', VERSIONS),
                 ([IDS[0], '0' + IDS[0]], 'Drama', VERSIONS)]
        for value in ('no-id', '1.5', '0', '-1', '2147483648', None, True, 1.5):
            cases.append(([value], 'Drama', VERSIONS))
        for genre in ('', 'Unknown Genre', "Drama'; DELETE FROM movies;--", None):
            cases.append((IDS, genre, VERSIONS))
        for version in ('', 'old', 'g' * 64, None):
            cases.append((IDS, 'Drama', {**VERSIONS, IDS[1]: version}))
        cases.append((IDS, 'Drama', {}))
        for ids, genre, versions in cases:
            with self.subTest(ids=ids, genre=genre, versions=versions):
                with self.assertRaises(ValueError):
                    repository.update_movie_genres(ids, genre, versions)
        connect.assert_not_called()


class GenreRepositoryTests(unittest.TestCase):
    def setUp(self):
        patch.dict(os.environ, {'DATABASE_DSN': 'mock-only'}).start()
        self.connect = patch.object(repository.psycopg, 'connect').start()
        self.addCleanup(patch.stopall)
        self.conn = self.connect.return_value.__enter__.return_value
        self.transaction = self.conn.transaction.return_value
        self.first_write = result({'movie_id': FIRST['movie_id']})
        self.conn.execute.side_effect = [result(FIRST), self.first_write,
                                         result(SECOND), result({'movie_id': SECOND['movie_id']})]

    def test_one_connection_one_transaction_ordered_parameterized_updates(self):
        self.assertEqual(repository.update_movie_genres(IDS[::-1], 'Drama', VERSIONS), 2)
        self.connect.assert_called_once()
        self.conn.transaction.assert_called_once_with()
        calls = self.conn.execute.call_args_list
        for index, movie in enumerate((FIRST, SECOND)):
            select, update = calls[index * 2:index * 2 + 2]
            self.assertIn('FOR UPDATE', select.args[0])
            self.assertEqual(select.args[1], (movie['movie_id'],))
            self.assertIn('SET genre = %s', update.args[0])
            self.assertIn('RETURNING movie_id', update.args[0])
            self.assertNotIn('Drama', update.args[0])
            self.assertEqual(update.args[1], ('Drama', movie['movie_id']))
        self.transaction.__exit__.assert_called_once_with(None, None, None)
        self.conn.commit.assert_not_called()
        self.conn.rollback.assert_not_called()

    def test_stale_second_movie_fails_after_first_update(self):
        # Simulates Tab B changing synopsis but leaving the original genre.
        self.conn.execute.side_effect = [result(FIRST), self.first_write,
                                         result({**SECOND, 'synopsis': SECOND['synopsis'] + ' Changed in Tab B.'})]
        with self.assertRaises(repository.StaleMovie):
            repository.update_movie_genres(IDS[::-1], 'Drama', VERSIONS)
        self.assertEqual(self.conn.execute.call_count, 3)
        self.assertIn('UPDATE ', self.conn.execute.call_args_list[1].args[0])
        self.first_write.fetchone.assert_called_once()
        self.assertIs(self.transaction.__exit__.call_args.args[0], repository.StaleMovie)
        self.assertIs(self.connect.return_value.__exit__.call_args.args[0], repository.StaleMovie)

    def test_missing_second_movie_escapes_transaction_after_first_update(self):
        self.conn.execute.side_effect = [result(FIRST), self.first_write, result(None)]
        with self.assertRaises(repository.MovieNotFound):
            repository.update_movie_genres(IDS, 'Drama', VERSIONS)
        self.assertEqual(self.conn.execute.call_count, 3)
        self.assertIs(self.transaction.__exit__.call_args.args[0], repository.MovieNotFound)

    def test_database_failure_on_second_update_escapes_transaction(self):
        self.conn.execute.side_effect = [result(FIRST), self.first_write, result(SECOND),
                                         psycopg.errors.CheckViolation('private detail')]
        with self.assertRaises(psycopg.errors.CheckViolation):
            repository.update_movie_genres(IDS, 'Drama', VERSIONS)
        self.assertEqual(self.conn.execute.call_count, 4)
        self.assertIs(self.transaction.__exit__.call_args.args[0], psycopg.errors.CheckViolation)

    def test_wrong_update_count_or_returned_id_escapes_transaction(self):
        for row, count in ((None, 0), ({'movie_id': 123}, 1), ({'movie_id': SECOND['movie_id']}, 2)):
            with self.subTest(row=row, count=count):
                self.conn.execute.side_effect = [result(FIRST), self.first_write,
                                                 result(SECOND), result(row, count)]
                with self.assertRaises(RuntimeError):
                    repository.update_movie_genres(IDS, 'Drama', VERSIONS)
                self.assertIs(self.transaction.__exit__.call_args.args[0], RuntimeError)

    def test_search_versions_use_exactly_the_displayed_snapshot(self):
        self.conn.execute.side_effect = None
        row = {key: value for key, value in FIRST.items() if key != 'genre'}
        self.conn.execute.return_value.fetchall.return_value = [{**row, 'category': FIRST['genre']}]
        rows = repository.search_movies('test')
        self.assertEqual(rows[0]['version'], VERSIONS[IDS[0]])
        self.conn.execute.assert_called_once()


class GenreRouteTests(unittest.TestCase):
    def setUp(self):
        web.app.testing = True
        self.client = web.app.test_client()
        self.rows = [{**movie, 'category': movie['genre'], 'version': VERSIONS[str(movie['movie_id'])]}
                     for movie in (FIRST, SECOND)]
        self.search = patch.object(web, 'search_movies', return_value=self.rows).start()
        self.update = patch.object(web, 'update_movie_genres', return_value=2).start()
        self.addCleanup(patch.stopall)
        self.form = MultiDict([('movie_ids', movie_id) for movie_id in IDS] +
                              [(f'version_{movie_id}', version) for movie_id, version in VERSIONS.items()] +
                              [('genre', 'Drama'), ('q', 'test')])

    def test_home_has_checkboxes_versions_and_genre_options(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Update Selected Movies', response.text)
        self.assertEqual(response.text.count('name="movie_ids"'), 2)
        for movie_id, version in VERSIONS.items():
            self.assertIn(f'name="version_{movie_id}" value="{version}"', response.text)
        self.assertIn('<option value="Drama">Drama</option>', response.text)
        self.update.assert_not_called()

    def test_success_redirects_and_refresh_does_not_resubmit(self):
        response = self.client.post('/movies/genres', data=self.form)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.location, '/?q=test')
        self.update.assert_called_once_with(IDS, 'Drama', VERSIONS)
        page = self.client.get(response.location)
        self.assertIn('Updated the genre for all 2 selected movies.', page.text)
        self.client.get(response.location)
        self.update.assert_called_once()

    def test_conflict_and_database_errors_do_not_expose_details(self):
        for error, status, message in (
            (repository.StaleMovie(), 409, 'changed after you opened'),
            (repository.MovieNotFound(), 409, 'no longer exists'),
            (psycopg.errors.CheckViolation('private detail'), 409, 'rolled back'),
            (RuntimeError('private detail'), 409, 'rolled back'),
            (psycopg.OperationalError('private detail'), 503, 'could not confirm'),
            (KeyError('private detail'), 503, 'could not confirm'),
        ):
            with self.subTest(error=type(error).__name__):
                self.update.side_effect = error
                response = self.client.post('/movies/genres', data=self.form)
                self.assertEqual(response.status_code, status)
                self.assertIn(message, response.text)
                self.assertNotIn('private detail', response.text)
                self.assertNotIn('checked', response.text)
                self.assertNotIn('Updated the genre', response.text)

    def test_invalid_forms_use_real_validation_without_connecting(self):
        self.update.side_effect = repository.update_movie_genres
        with patch.object(repository.psycopg, 'connect') as connect:
            for field, values in (('movie_ids', []), ('movie_ids', IDS + [IDS[0]]),
                                  ('movie_ids', ['bad']), ('genre', ['Invalid']),
                                  (f'version_{IDS[0]}', [''])):
                with self.subTest(field=field, values=values):
                    form = self.form.copy()
                    form.setlist(field, values)
                    response = self.client.post('/movies/genres', data=form)
                    self.assertEqual(response.status_code, 400)
                    self.assertIn('No genre changes were saved.', response.text)
            connect.assert_not_called()

    def test_database_failure_while_rendering_does_not_hide_error(self):
        self.update.side_effect = repository.StaleMovie()
        self.search.side_effect = psycopg.OperationalError('private detail')
        response = self.client.post('/movies/genres', data=self.form)
        self.assertEqual(response.status_code, 503)
        self.assertIn('rolled back', response.text)
        self.assertIn('movie list is temporarily unavailable', response.text)
        self.assertNotIn('No matching records yet.', response.text)
        self.assertNotIn('private detail', response.text)

    def test_bulk_endpoint_requires_post(self):
        self.assertEqual(self.client.get('/movies/genres').status_code, 405)
        self.update.assert_not_called()


if __name__ == '__main__':
    unittest.main()
