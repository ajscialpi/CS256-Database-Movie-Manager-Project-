r"""Optional browser evidence against the isolated King's app through an SSH tunnel.

Requires Playwright and installed Chrome, plus existing SSH access to King's.
Run from the repository root while the M08 server/tunnel in M08_SETUP.md runs:
    .venv\Scripts\python.exe tests/verify_m08_browser.py
Only the newly created disposable movie is changed or deleted.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import subprocess

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:55108'
IMAGES = ROOT / 'MileStones' / 'MileStoneImages'


def database_snapshot():
    script = '''import json, psycopg
from psycopg.rows import dict_row
with psycopg.connect('dbname=antonioscialpi', row_factory=dict_row) as conn:
    print(json.dumps({
        'movies': conn.execute('SELECT * FROM cs256_m05_movievault.movies ORDER BY movie_id').fetchall(),
        'reviews': conn.execute('SELECT * FROM cs256_m05_movievault.reviews ORDER BY review_id').fetchall(),
    }, default=str))
'''
    result = subprocess.run(
        ['ssh', '-T', '-o', 'BatchMode=yes', 'antonioscialpi@cs256.kings.edu',
         'cs256-project/.venv-kings/bin/python', '-B', '-'],
        input=script, text=True, capture_output=True, check=True, timeout=30,
    )
    return json.loads(result.stdout)


def main():
    before = database_snapshot()
    movie_id = secrets.randbelow(100000000) + 1900000000
    assert all(row['movie_id'] != movie_id for row in before['movies'])
    title = f'M08 Browser Test {movie_id}'
    path = f'/movies/{movie_id}'
    form = {
        'movie_id': str(movie_id), 'title': title, 'genre': 'Mystery',
        'release_year': '2026', 'director': 'Jordan Example', 'content_rating': 'PG',
        'synopsis': 'A fictional movie used only for the M08 browser verification.',
    }
    evidence = {'verified_at_utc': datetime.now(timezone.utc).isoformat(),
                'method': "Automated Chrome browser through SSH to the isolated King's M08 app; separate PostgreSQL SELECTs through SSH verify stored values.",
                'movie_id': movie_id}

    def current():
        return next((row for row in database_snapshot()['movies'] if row['movie_id'] == movie_id), None)

    IMAGES.mkdir(parents=True, exist_ok=True)
    created = False
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome', headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 1000})
        page = context.new_page()
        try:
            assert page.goto(BASE + '/movies/new').status == 200
            for field, value in form.items():
                page.locator(f'[name="{field}"]').fill(value)
            with page.expect_response(lambda r: r.request.method == 'POST') as saved:
                page.get_by_role('button', name='Save movie', exact=True).click()
            assert saved.value.status == 303
            created = True
            page.wait_for_url(BASE + path)
            original = current()
            assert original and original['title'] == title
            page.screenshot(path=str(IMAGES / 'M08BeforeUpdate.png'), full_page=True)

            tab_a = context.new_page()
            tab_b = context.new_page()
            delete_tab = context.new_page()
            tab_a.goto(BASE + path + '/edit')
            tab_b.goto(BASE + path + '/edit')
            delete_tab.goto(BASE + path + '/delete')
            tab_a.screenshot(path=str(IMAGES / 'M08EditForm.png'), full_page=True)
            tab_a.locator('[name="title"]').fill(title + ' - Updated')
            tab_a.locator('[name="genre"]').fill('Drama')
            with tab_a.expect_response(lambda r: r.request.method == 'POST') as saved:
                tab_a.get_by_role('button', name='Save changes').click()
            assert saved.value.status == 303
            tab_a.wait_for_url(BASE + path)
            updated = current()
            assert updated == {**original, 'title': title + ' - Updated', 'genre': 'Drama'}
            tab_a.screenshot(path=str(IMAGES / 'M08AfterUpdate.png'), full_page=True)
            evidence['update'] = {'http_status': saved.value.status, 'before': original, 'after': updated}

            with tab_b.expect_response(lambda r: r.request.method == 'POST') as stale:
                tab_b.get_by_role('button', name='Save changes').click()
            assert stale.value.status == 409
            tab_b.get_by_role('alert').wait_for()
            assert current() == updated
            tab_b.screenshot(path=str(IMAGES / 'M08StaleEdit.png'), full_page=True)
            evidence['stale_edit'] = {'http_status': stale.value.status, 'after': updated}
            with delete_tab.expect_response(lambda r: r.request.method == 'POST') as stale:
                delete_tab.get_by_role('button', name='Delete movie', exact=True).click()
            assert stale.value.status == 409 and current() == updated
            evidence['stale_delete'] = {'http_status': stale.value.status, 'unchanged': True}

            page.goto(BASE + path + '/delete')
            page.screenshot(path=str(IMAGES / 'M08DeleteConfirmation.png'), full_page=True)
            page.get_by_role('link', name='Cancel', exact=True).click()
            page.wait_for_url(BASE + path)
            assert current() == updated
            evidence['cancel'] = {'before': updated, 'after': current(), 'returned_to_detail': True}

            page.set_viewport_size({'width': 375, 'height': 812})
            page.goto(BASE + path + '/edit')
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            page.screenshot(path=str(IMAGES / 'M08EditNarrow.png'), full_page=True)
            evidence['narrow_edit'] = {'viewport_width': 375, 'no_horizontal_overflow': True}
            page.set_viewport_size({'width': 1280, 'height': 1000})

            page.goto(BASE + path + '/delete')
            with page.expect_response(lambda r: r.request.method == 'POST') as deleted:
                page.get_by_role('button', name='Delete movie', exact=True).click()
            assert deleted.value.status == 303
            page.wait_for_url(BASE + '/')
            assert current() is None
            created = False
            evidence['delete'] = {'http_status': deleted.value.status, 'before': updated, 'after': None}
        finally:
            if created:
                # Never clean up an existing movie: creation must have succeeded,
                # and the database row must still have this run's unique title.
                row = current()
                if row and row['title'] in (title, title + ' - Updated'):
                    page.goto(BASE + path + '/delete')
                    page.get_by_role('button', name='Delete movie', exact=True).click()
                    page.wait_for_url(BASE + '/')
            browser.close()
    assert database_snapshot() == before
    evidence['all_existing_movies_and_reviews_unchanged'] = True
    evidence['result'] = 'PASS'
    output = ROOT / 'MileStones' / 'M08-browser-verification.json'
    output.write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'result': 'PASS', 'movie_id': movie_id, 'evidence': str(output)}, indent=2))


if __name__ == '__main__':
    main()
