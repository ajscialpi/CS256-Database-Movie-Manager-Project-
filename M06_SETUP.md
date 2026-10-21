# M06: upload, run, and collect evidence

The implementation is in the local project. Run these commands yourself to
transfer it to King's and demonstrate a real PostgreSQL write. No table
alteration or new dependency is required. The application detects both the
local and server template layouts automatically.

## 1. Upload from Windows PowerShell

Open PowerShell in the repository folder (not inside an SSH session).
If Flask is currently running on King's, stop it with Ctrl+C in its server
terminal before uploading. These commands replace the matching server files.

```powershell
scp .\backendconnection\app.py .\backendconnection\validation.py .\backendconnection\repository_postgres.py antonioscialpi@cs256.kings.edu:~/cs256-project/
scp .\templates\index.html .\templates\add_movie.html .\templates\movie_detail.html .\templates\brand.css antonioscialpi@cs256.kings.edu:~/cs256-project/templates/
ssh antonioscialpi@cs256.kings.edu
```

## 2. Start Flask inside the King's SSH terminal

```bash
cd ~/cs256-project
export DATABASE_DSN="dbname=$(whoami)"
PYTHONDONTWRITEBYTECODE=1 .venv-kings/bin/python -m flask --app app:app --no-debug run --host 127.0.0.1 --port 5108 --no-debugger --no-reload
```

Leave this terminal running. If the port is already in use, stop your earlier
Flask process in its original terminal, then retry.

## 3. Open the tunnel in a second Windows PowerShell terminal

If your existing tunnel is still running, reuse it instead of starting another.

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:55100:127.0.0.1:5108 antonioscialpi@cs256.kings.edu
```

Leave this terminal running. Open http://127.0.0.1:55100/movies/new in your browser.

## 4. Open PostgreSQL in a third Windows PowerShell terminal

```powershell
ssh antonioscialpi@cs256.kings.edu
```

Then, inside King's:

```bash
psql -d antonioscialpi
```

Run the following at the PostgreSQL prompt:

```sql
SELECT movie_id, title FROM cs256_m05_movievault.movies
WHERE movie_id IN (9001, 9002);
SELECT COUNT(*) AS movie_count FROM cs256_m05_movievault.movies;
```

Use 9001 and 9002 below only if neither exists. Otherwise choose two unused
positive integer IDs and substitute them in the form and queries.
Record the count before saving.

## 5. Save a valid movie in the browser

| Field | Value |
| --- | --- |
| Movie ID | 9001 (if unused) |
| Title | Sample Film: Midnight Library |
| Genre | Mystery |
| Release year | 2026 |
| Director | Jordan Example |
| Content rating | PG |
| Synopsis | A fictional librarian discovers a hidden room containing clues to a forgotten town mystery. |

Click **Save movie**. The browser should redirect to `/movies/9001` and show
the stored values. In PostgreSQL run:

```sql
SELECT * FROM cs256_m05_movievault.movies WHERE movie_id = 9001;
SELECT COUNT(*) AS movie_count FROM cs256_m05_movievault.movies;
```

Save a screenshot of the detail page and database result. With no other writes,
the count should increase by one. Refresh the detail page once and run these
queries again: the row and count should stay the same.

## 6. Reject invalid input in the browser

Open **Add another movie**. Enter the same valid values with the other unused
ID (9002), but use `Short` as the synopsis. Click **Save movie**. Expect the
message `Enter between 20 and 1,000 characters.` beside the synopsis.

In PostgreSQL run:

```sql
SELECT * FROM cs256_m05_movievault.movies WHERE movie_id = 9002;
SELECT COUNT(*) AS movie_count FROM cs256_m05_movievault.movies;
```

Expect zero rows for the rejected ID and the same count as after the successful
save. Capture the validation message and query results. Keep the other fields
valid so this test isolates synopsis validation.

## 7. Finish the submission

The completed report is in `MileStones/M06.md`, with browser screenshots and
real database results in `MileStones/M06-verification.json`. The automated
server check used Flask's test client with PostgreSQL, not a manual browser
refresh. Review those results and any additional browser checks you perform.
Submit the form, routes, validator, database module, and detail
template (or the assigned repository commit link), plus the evidence and AI-use
note. Do not claim the database checks succeeded until you run them.

Post/Redirect/Get means the successful POST inserts and commits once, then a
303 redirect takes the browser to a GET detail page. Refresh repeats the GET,
which only reads. Separately submitting a new valid form can create another row;
reusing an existing ID is rejected by the primary key and shown as a field error.

## Optional: repeat the local automated checks

In Windows PowerShell, in the repository folder:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

These checks mock database calls. They verify validation, routing, parameter
binding, and refresh behavior, but do not prove a real PostgreSQL write.

To repeat the separate real-database checks from Windows PowerShell:

```powershell
Get-Content -Raw .\tests\verify_m06_server.py | ssh antonioscialpi@cs256.kings.edu "cd ~/cs256-project && DATABASE_DSN=dbname=antonioscialpi .venv-kings/bin/python -"
```

This requires saved movie 9001 to exist and ID 9002 to be absent. It uses the
uploaded app and database, sends two invalid POSTs, and repeats the saved-record
GET. It does not create a new valid movie and does not require Flask to be
listening on port 5108. A successful run prints JSON ending with `"result": "PASS"`.
