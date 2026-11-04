# M08: run and repeat the checks

M08 adds edit/delete to the existing Flask application. No schema change or new
runtime dependency is required. The real database checks and screenshots were
collected using an isolated copy in `~/cs256-project/.m08-verification-20261103`
with the existing King's PostgreSQL database. Only newly created disposable
movies and a disposable review were changed or deleted.

## Local checks

From the repository root in Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q backendconnection tests
```

The 31 unit tests use mocks; they do not prove a PostgreSQL write. The two
`verify_m08_*.py` scripts below run separate real database checks.

## Upload and use the normal King's app

Stop the existing Flask process with Ctrl+C in its own terminal before uploading.
From Windows PowerShell in the repository root:

```powershell
scp .\backendconnection\app.py .\backendconnection\repository_postgres.py .\backendconnection\validation.py antonioscialpi@cs256.kings.edu:~/cs256-project/
scp .\templates\index.html .\templates\add_movie.html .\templates\movie_detail.html .\templates\edit_movie.html .\templates\delete_movie.html .\templates\brand.css antonioscialpi@cs256.kings.edu:~/cs256-project/templates/
scp .\tests\verify_m08_server.py antonioscialpi@cs256.kings.edu:~/cs256-project/
ssh antonioscialpi@cs256.kings.edu
```

Inside King's:

```bash
cd ~/cs256-project
export DATABASE_DSN="dbname=$(whoami)"
PYTHONDONTWRITEBYTECODE=1 .venv-kings/bin/python -m flask --app app:app --no-debug run --host 127.0.0.1 --port 5108 --no-debugger --no-reload
```

In a second Windows PowerShell terminal (reuse an existing tunnel if open):

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:55100:127.0.0.1:5108 antonioscialpi@cs256.kings.edu
```

Open http://127.0.0.1:55100/, select a movie, and use **Edit movie** or
**Delete movie**. GET only displays the form. **Cancel** returns to details;
only the explicit **Delete movie** button submits deletion.

## Repeat the real PostgreSQL checks

In a separate King's terminal after uploading the script:

```bash
cd ~/cs256-project
export DATABASE_DSN="dbname=$(whoami)"
.venv-kings/bin/python -B verify_m08_server.py
```

This creates a new randomly numbered movie and review, verifies update/cancel/
stale forms/foreign-key restrictions, deletes only its test records, and checks
that all pre-existing movies and reviews are unchanged. It prints JSON ending
with `"result": "PASS"` only if all assertions succeed. Run when no one else is
editing the database because the final comparison checks all existing rows.
The saved run is [MileStones/M08-verification.json](MileStones/M08-verification.json).

## Repeat the automated browser screenshots

The browser script uses installed Google Chrome and optional Playwright tooling.
Playwright is needed only for this script, not for MovieVault or its unit tests.
It connects to port **55108** and makes independent PostgreSQL reads over SSH.
It requires working SSH authentication before it can run.

From Windows PowerShell, prepare the isolated copy:

```powershell
ssh antonioscialpi@cs256.kings.edu 'mkdir -p ~/cs256-project/.m08-verification-20261103/templates'
scp .\backendconnection\app.py .\backendconnection\repository_postgres.py .\backendconnection\validation.py .\tests\verify_m08_server.py antonioscialpi@cs256.kings.edu:~/cs256-project/.m08-verification-20261103/
scp .\templates\index.html .\templates\add_movie.html .\templates\movie_detail.html .\templates\edit_movie.html .\templates\delete_movie.html .\templates\brand.css antonioscialpi@cs256.kings.edu:~/cs256-project/.m08-verification-20261103/templates/
ssh -T -o ExitOnForwardFailure=yes -L 127.0.0.1:55108:127.0.0.1:5118 antonioscialpi@cs256.kings.edu 'cd ~/cs256-project/.m08-verification-20261103 && DATABASE_DSN=dbname=antonioscialpi ../.venv-kings/bin/python -B -m flask --app app:app --no-debug run --host 127.0.0.1 --port 5118 --no-debugger --no-reload'
```

Leave that terminal running. In another Windows PowerShell terminal:

```powershell
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe -B tests/verify_m08_browser.py
```

This creates and removes its own disposable movie. It saves actual Chrome
screenshots under `MileStones/MileStoneImages/M08*.png` and measured results in
`MileStones/M08-browser-verification.json`. A repeat run uses a different ID;
update the table in M08.md if replacing its evidence. Stop the isolated server
and tunnel with Ctrl+C afterward.

## Optional manual browser check

For a personal repeat of the already automated tests, use the normal app on
port 55100. In another King's terminal, open `psql -X -d antonioscialpi`.
Check that ID **98008** is unused before using it:

```sql
SELECT * FROM cs256_m05_movievault.movies WHERE movie_id = 98008;
```

If it exists, choose another unused positive integer and substitute it everywhere.
Create a disposable movie through **Add a movie**, with title `M08 Manual Test`,
genre `Mystery`, year `2026`, director `Jordan Example`, rating `PG`, and synopsis
`A fictional movie created only for a manual M08 workflow check.`

- Run the SELECT above and capture the database row and detail page before editing.
- Open `/movies/98008/edit` in two tabs and `/movies/98008/delete` in a third.
  In Tab A change the title to `M08 Manual Test Updated` and save. Repeat the
  SELECT and capture the updated row; the ID should still be 98008.
- In Tab B submit the older form. Capture its error and the POST's **409** status
  in browser Network tools. Repeat the SELECT to check that Tab A's values remain.
- Submit the older delete page; expect another 409 and the row to remain.
- Open a fresh delete page and capture the ID/title/Cancel interface. Click Cancel,
  repeat the SELECT, and capture the unchanged row.
- Open a fresh delete page and confirm deletion of this disposable movie. Repeat
  the SELECT and capture zero rows. Visiting its edit/delete URLs should now give 404.

Keep these separate from the committed automated results. Suggested screenshot
names are `M08ManualBefore.png`, `M08ManualAfter.png`, `M08ManualCancel.png`,
`M08ManualStale.png`, and `M08ManualDeleted.png`. Add Markdown image links only
after capturing the corresponding images.
