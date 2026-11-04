"""Local CRUD checks with mocked PostgreSQL; real evidence uses verify_m08_server.py."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backendconnection'))

import app as web
import repository_postgres as repository
from psycopg.errors import CheckViolation, ForeignKeyViolation
from validation import validate_movie
from test_movie_create import VALID


MOVIE, _ = validate_movie(VALID)
VERSION = repository.movie_version(MOVIE)


class CrudRouteTests(unittest.TestCase):
    def setUp(self):
        web.app.testing = True
        self.client = web.app.test_client()
        self.get = patch.object(web, 'get_movie', return_value=MOVIE.copy()).start()
        self.update = patch.object(web, 'update_movie').start()
        self.delete = patch.object(web, 'delete_movie').start()
        self.addCleanup(patch.stopall)

    def test_edit_prefills_all_details_without_editable_id(self):
        response = self.client.get('/movies/9001/edit')
        self.assertEqual(response.status_code, 200)
        for field in VALID.keys() - {'movie_id'}:
            self.assertIn(f'name="{field}"', response.text)
            self.assertIn(str(MOVIE[field]), response.text)
        self.assertNotIn('name="movie_id"', response.text)
        self.assertIn(VERSION, response.text)
        self.update.assert_not_called()

    def test_update_uses_url_id_and_redirects_to_same_record(self):
        response = self.client.post('/movies/9001/edit', data={
            **VALID, 'movie_id': '123', 'title': "O'Brien", 'version': VERSION,
        })
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.location, '/movies/9001')
        self.update.assert_called_once_with(9001, {**MOVIE, 'title': "O'Brien"}, VERSION)

    def test_edit_validation_preserves_inputs_and_original_version(self):
        response = self.client.post('/movies/9001/edit', data={
            **VALID, 'synopsis': 'Short', 'version': 'old-version',
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('Short', response.text)
        self.assertIn('old-version', response.text)
        self.assertIn('Enter between 20 and 1,000 characters.', response.text)
        self.update.assert_not_called()

    def test_stale_edit_returns_409_without_refreshing_token(self):
        self.update.side_effect = repository.StaleMovie
        response = self.client.post('/movies/9001/edit', data={**VALID, 'version': 'old'})
        self.assertEqual(response.status_code, 409)
        self.assertIn('Your changes were not saved', response.text)
        self.assertIn('value="old"', response.text)
        self.assertNotIn(VERSION, response.text)

    def test_database_constraint_error_is_readable(self):
        self.update.side_effect = CheckViolation('private database detail')
        response = self.client.post('/movies/9001/edit', data={**VALID, 'version': VERSION})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('private database detail', response.text)

    def test_delete_get_and_cancel_only_read(self):
        response = self.client.get('/movies/9001/delete')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Movie ID: 9001', response.text)
        self.assertIn(VALID['title'], response.text)
        self.assertIn('href="/movies/9001">Cancel</a>', response.text)
        self.assertEqual(self.client.get('/movies/9001').status_code, 200)
        self.delete.assert_not_called()

    def test_delete_requires_explicit_confirmation(self):
        for confirmation in ('', 'no', 'true'):
            response = self.client.post('/movies/9001/delete', data={
                'version': VERSION, 'confirm': confirmation,
            })
            self.assertEqual(response.status_code, 400)
        self.delete.assert_not_called()

    def test_confirmed_delete_redirects_home(self):
        response = self.client.post('/movies/9001/delete', data={
            'version': VERSION, 'confirm': 'yes',
        })
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.location, '/')
        self.delete.assert_called_once_with(9001, VERSION)

    def test_stale_delete_and_foreign_key_are_safe_conflicts(self):
        for exception, message in (
            (repository.StaleMovie(), 'Nothing was deleted'),
            (ForeignKeyViolation('private detail'), 'related records'),
        ):
            with self.subTest(exception=type(exception).__name__):
                self.delete.side_effect = exception
                response = self.client.post('/movies/9001/delete', data={
                    'version': VERSION, 'confirm': 'yes',
                })
                self.assertEqual(response.status_code, 409)
                self.assertIn(message, response.text)
                self.assertNotIn('private detail', response.text)

    def test_missing_or_out_of_range_movies_return_404_for_get_and_post(self):
        self.get.return_value = None
        for movie_id in (9999, 2147483648, 0):
            for action in ('edit', 'delete'):
                for method in (self.client.get, self.client.post):
                    self.assertEqual(method(f'/movies/{movie_id}/{action}').status_code, 404)
        self.update.assert_not_called()
        self.delete.assert_not_called()

    def test_movie_deleted_between_route_read_and_transaction_returns_404(self):
        self.update.side_effect = repository.MovieNotFound
        self.delete.side_effect = repository.MovieNotFound
        self.assertEqual(self.client.post('/movies/9001/edit', data={
            **VALID, 'version': VERSION,
        }).status_code, 404)
        self.assertEqual(self.client.post('/movies/9001/delete', data={
            'confirm': 'yes', 'version': VERSION,
        }).status_code, 404)

    @patch.object(web, 'search_movies')
    def test_search_matching_empty_blank_and_apostrophe(self, search):
        for query in ('Midnight Library', 'NO-SUCH-MOVIE-XYZ', '', "O'Brien"):
            search.return_value = [] if query == 'NO-SUCH-MOVIE-XYZ' else [
                {**MOVIE, 'category': MOVIE['genre']},
            ]
            response = self.client.get('/', query_string={'q': query})
            self.assertEqual(response.status_code, 200)
            search.assert_called_with(query)
            if query == 'NO-SUCH-MOVIE-XYZ':
                self.assertIn('No matching records yet.', response.text)


class CrudRepositoryTests(unittest.TestCase):
    def setUp(self):
        patch.dict(os.environ, {'DATABASE_DSN': 'mock-only'}).start()
        self.connect = patch.object(repository.psycopg, 'connect').start()
        self.addCleanup(patch.stopall)
        self.conn = self.connect.return_value.__enter__.return_value
        self.lock = MagicMock()
        self.lock.fetchone.return_value = MOVIE.copy()
        self.write = MagicMock()
        self.write.fetchone.return_value = {'movie_id': 9001}
        self.write.rowcount = 1
        self.conn.execute.side_effect = [self.lock, self.write]

    def test_update_locks_then_binds_values_and_keeps_primary_key(self):
        values = {**MOVIE, 'title': "O'Brien", 'movie_id': 123}
        repository.update_movie(9001, values, VERSION)
        select, update = self.conn.execute.call_args_list
        self.assertIn('FOR UPDATE', select.args[0])
        self.assertEqual(select.args[1], (9001,))
        sql, params = update.args
        self.assertIn('WHERE movie_id = %s', sql)
        self.assertNotIn('SET movie_id', sql)
        self.assertNotIn("O'Brien", sql)
        self.assertEqual(params, ("O'Brien", 'Mystery', 2026,
                                  'Jordan Example', 'PG', VALID['synopsis'], 9001))
        self.connect.return_value.__exit__.assert_called_once_with(None, None, None)

    def test_delete_binds_only_selected_id(self):
        repository.delete_movie(9001, VERSION)
        sql, params = self.conn.execute.call_args.args
        self.assertIn('DELETE FROM cs256_m05_movievault.movies', sql)
        self.assertIn('WHERE movie_id = %s', sql)
        self.assertEqual(params, (9001,))

    def test_stale_missing_and_wrong_movie_tokens_never_write(self):
        other_version = repository.movie_version({**MOVIE, 'movie_id': 123})
        for version in ('', 'old', other_version):
            for action in (repository.update_movie, repository.delete_movie):
                self.conn.execute.reset_mock(side_effect=True)
                self.conn.execute.side_effect = [self.lock]
                with self.assertRaises(repository.StaleMovie):
                    if action is repository.update_movie:
                        action(9001, MOVIE, version)
                    else:
                        action(9001, version)
                self.assertEqual(self.conn.execute.call_count, 1)

    def test_missing_row_rolls_back(self):
        self.lock.fetchone.return_value = None
        with self.assertRaises(repository.MovieNotFound):
            repository.delete_movie(9001, VERSION)
        self.assertEqual(self.conn.execute.call_count, 1)
        self.assertIs(self.connect.return_value.__exit__.call_args.args[0], repository.MovieNotFound)

    def test_unexpected_row_counts_or_returned_id_roll_back(self):
        for count, row in ((0, None), (2, {'movie_id': 9001}), (1, {'movie_id': 999})):
            for action in (repository.update_movie, repository.delete_movie):
                self.conn.execute.side_effect = [self.lock, self.write]
                self.write.rowcount = count
                self.write.fetchone.return_value = row
                with self.assertRaises(RuntimeError):
                    if action is repository.update_movie:
                        action(9001, MOVIE, VERSION)
                    else:
                        action(9001, VERSION)
                self.assertIs(self.connect.return_value.__exit__.call_args.args[0], RuntimeError)

    def test_foreign_key_error_exits_transaction_with_rollback(self):
        self.conn.execute.side_effect = [self.lock, ForeignKeyViolation()]
        with self.assertRaises(ForeignKeyViolation):
            repository.delete_movie(9001, VERSION)
        self.assertIs(self.connect.return_value.__exit__.call_args.args[0], ForeignKeyViolation)

    def test_every_stored_field_affects_version(self):
        for field in MOVIE:
            self.assertNotEqual(VERSION, repository.movie_version({**MOVIE, field: 'changed'}))

    def test_search_sql_is_parameterized_and_ordered(self):
        self.conn.execute.side_effect = None
        repository.search_movies("  O'Brien  ")
        sql, params = self.conn.execute.call_args.args
        self.assertNotIn("O'Brien", sql)
        self.assertIn('ORDER BY title ASC, movie_id ASC', sql)
        self.assertIn('LIMIT 25', sql)
        self.assertEqual(params, ("%O'Brien%",))


if __name__ == '__main__':
    unittest.main()
