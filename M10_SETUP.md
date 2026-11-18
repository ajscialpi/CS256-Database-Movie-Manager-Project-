# M10: run and capture the transaction evidence

The implementation needs no schema changes or new dependencies. The actual
PostgreSQL failure/retry demonstration has not been run. Work through one step
at a time and stop if a command or result differs from the instructions.

## 1. Local checks

In Windows PowerShell at the repository root:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
git diff --check
```

The implementation run passed all 52 tests. Database calls in these unit tests
are mocked. They check request validation, SQL parameters, transaction scope,
and that the first UPDATE precedes the stale second record. They are not the
database evidence required for M10.

An implementation-time Chrome check also passed at 1280px and 390px for layout,
selection, the conflict response, reselection, and the success redirect. It used
synthetic rows and mocked writes; it did not create submission screenshots.

## 2. Upload and start the existing King's app

Stop the old Flask process with Ctrl+C in its terminal. In Windows PowerShell
at the repository root, upload the application files and existing templates/SQL
so the server's flat layout includes both M09 and M10:

```powershell
ssh antonioscialpi@cs256.kings.edu 'mkdir -p ~/cs256-project/templates ~/cs256-project/sql ~/cs256-project/m10-evidence'
scp .\backendconnection\app.py .\backendconnection\repository_postgres.py .\backendconnection\validation.py antonioscialpi@cs256.kings.edu:~/cs256-project/
scp .\templates\index.html .\templates\add_movie.html .\templates\edit_movie.html .\templates\delete_movie.html .\templates\movie_detail.html .\templates\movie_review_report.html .\templates\brand.css antonioscialpi@cs256.kings.edu:~/cs256-project/templates/
scp .\sql\m09_movie_review_report.sql antonioscialpi@cs256.kings.edu:~/cs256-project/sql/
ssh antonioscialpi@cs256.kings.edu
```

In the King's terminal:

```bash
cd ~/cs256-project
export DATABASE_DSN="dbname=$(whoami)"
.venv-kings/bin/python -B -m flask --app app:app --no-debug run --host 127.0.0.1 --port 5108 --no-debugger --no-reload
```

Leave this running. In a second Windows PowerShell terminal, reuse the existing
tunnel if it is running, or start it:

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:55100:127.0.0.1:5108 antonioscialpi@cs256.kings.edu
```

Open <http://127.0.0.1:55100/>. Confirm **Update Movie Genres**, the genre
dropdown, and movie checkboxes appear. Stop here and report any startup problem
before creating test data. Existing movie details still provide Edit and Delete.

## 3. Create two disposable records and record their original values

In a third Windows PowerShell terminal:

```powershell
ssh antonioscialpi@cs256.kings.edu
```

In that King's terminal:

```bash
cd ~/cs256-project
psql -X -v ON_ERROR_STOP=1 -d antonioscialpi
```

At the `psql` prompt, check these **candidate** IDs. They are suggestions, not
verified unused IDs or recorded results:

```sql
\pset pager off
SELECT movie_id, title, genre
FROM cs256_m05_movievault.movies
WHERE movie_id IN (98101, 98102)
ORDER BY movie_id;
```

Proceed only if the query returns zero rows. If either ID is already used, stop
and choose/check two different IDs. Never overwrite an existing record for this
test. Use **Add a movie** to create the following disposable records, substituting
the checked IDs if needed:

| Field | Lower-ID movie | Higher-ID movie |
| --- | --- | --- |
| Movie ID | 98101 (only if unused) | 98102 (only if unused) |
| Title | M10 Disposable A | M10 Disposable B |
| Genre | Mystery | Comedy |
| Release year | 2026 | 2026 |
| Director | Jordan Example | Jordan Example |
| Content rating | PG | PG |
| Synopsis | A disposable movie used to verify the M10 transaction and rollback. | Another disposable movie used to verify the M10 transaction and rollback. |

In the same `psql` session, set variables to the **actual IDs you just created**:

```sql
\set first_id 98101
\set second_id 98102
\o m10-evidence/M10OriginalRecords.txt
SELECT movie_id, title, genre, synopsis
FROM cs256_m05_movievault.movies
WHERE movie_id IN (:first_id, :second_id)
ORDER BY movie_id;
\o
SELECT movie_id, title, genre, synopsis
FROM cs256_m05_movievault.movies
WHERE movie_id IN (:first_id, :second_id)
ORDER BY movie_id;
```

The first SELECT saves the real output; the second displays it for inspection.
Confirm two rows with the IDs, titles, and original genres actually entered.
Optionally capture `M10OriginalRecords.png`. Send the actual result before moving
on. Keep this `psql` session open so the variables remain defined. If reconnecting,
set the two variables again. Run evidence SELECTs outside an explicit transaction
so each sees the latest committed state.

## 4. Save the independent change and capture the pre-failure state

1. Open <http://127.0.0.1:55100/?q=M10+Disposable> in **Tab A** and **Tab B**.
2. In Tab A, select both disposable movies and choose **Drama**. Do not submit yet.
3. In Tab B, open the **higher movie ID**, choose **Edit movie**, append
   ` Changed in Tab B.` to the synopsis, and save. Leave its genre unchanged.
4. Do not refresh Tab A. Confirm Tab B's detail page contains the new synopsis.

In `psql`, save and display the state immediately before the bulk attempt:

```sql
\o m10-evidence/M10BeforeFailure.txt
SELECT movie_id, title, genre, synopsis
FROM cs256_m05_movievault.movies
WHERE movie_id IN (:first_id, :second_id)
ORDER BY movie_id;
\o
SELECT movie_id, title, genre, synopsis
FROM cs256_m05_movievault.movies
WHERE movie_id IN (:first_id, :second_id)
ORDER BY movie_id;
```

Capture the displayed SQL and both rows as `M10BeforeFailure.png`. Make the
terminal wide enough to show the synopsis. Check both original genres and the
higher-ID movie's saved Tab B text. This is the failure's **before** snapshot.

## 5. Submit the stale selection and verify rollback

In the unrefreshed Tab A, click **Update Selected Movies**. Expected result:
an error stating that a movie changed, the transaction was rolled back, and no
genre changes were saved. Capture `M10RollbackMessage.png`; the POST in browser
Network tools should have status **409**.

The function sorts IDs numerically. It locks/checks/updates the lower ID, then
locks/checks the higher ID. Only the second movie was edited in Tab B, so the
first UPDATE runs before the second movie's stale version raises an exception.
That exception exits `conn.transaction()` and rolls back the first UPDATE.

Immediately query the actual database:

```sql
\o m10-evidence/M10AfterRollback.txt
SELECT movie_id, title, genre, synopsis
FROM cs256_m05_movievault.movies
WHERE movie_id IN (:first_id, :second_id)
ORDER BY movie_id;
\o
SELECT movie_id, title, genre, synopsis
FROM cs256_m05_movievault.movies
WHERE movie_id IN (:first_id, :second_id)
ORDER BY movie_id;
```

Capture `M10AfterRollback.png`. Compare the output with `M10BeforeFailure.txt`:
both genres should still be their original values, and the higher-ID synopsis
should still include `Changed in Tab B.`. That separate edit committed before
the failed transaction, so the rollback should not undo it. Stop and report the
actual error and both rows before retrying. Do not label an unexpected result a pass.

## 6. Refresh, record the pre-retry state, and retry successfully

Refresh Tab A by reopening <http://127.0.0.1:55100/?q=M10+Disposable> as a GET;
do not accept a browser prompt to resend the failed POST. Review both movies and
the saved synopsis. Select both movies again and choose **Drama**, but first save
the current database values:

```sql
\o m10-evidence/M10BeforeRetry.txt
SELECT movie_id, title, genre, synopsis
FROM cs256_m05_movievault.movies
WHERE movie_id IN (:first_id, :second_id)
ORDER BY movie_id;
\o
SELECT movie_id, title, genre, synopsis
FROM cs256_m05_movievault.movies
WHERE movie_id IN (:first_id, :second_id)
ORDER BY movie_id;
```

Capture `M10BeforeRetry.png`. Without making any other edits, click
**Update Selected Movies**. Expected result: a success message for both movies,
a redirect back to the list, and both cards showing Drama. Capture
`M10RetrySuccess.png`. Then immediately save/query:

```sql
\o m10-evidence/M10AfterRetry.txt
SELECT movie_id, title, genre, synopsis
FROM cs256_m05_movievault.movies
WHERE movie_id IN (:first_id, :second_id)
ORDER BY movie_id;
\o
SELECT movie_id, title, genre, synopsis
FROM cs256_m05_movievault.movies
WHERE movie_id IN (:first_id, :second_id)
ORDER BY movie_id;
```

Capture `M10AfterRetry.png`. Both stored genres should be Drama and the Tab B
synopsis should still exist. Preserve the before/after files even though the
before-retry values may match the after-rollback values. Send these actual results
so the milestone can be completed accurately.

## 7. Store evidence and finish the draft

Save the browser and terminal screenshots directly under
`MileStones/MileStoneImages/` on Windows, following the names above. From a Windows
PowerShell terminal at the repository root, copy the real database text results:

```powershell
scp 'antonioscialpi@cs256.kings.edu:~/cs256-project/m10-evidence/M10*.txt' .\MileStones\MileStoneImages\
```

After verifying the files, replace the placeholders in `MileStones/M10.md` with
actual IDs, values, and screenshot links. Do not claim a successful demonstration
from unit tests alone. Leave the disposable records in place until the evidence
is reviewed; optional cleanup afterward should use each test movie's existing
delete confirmation page. No automatic cleanup, commit, or push is part of this
walkthrough.
