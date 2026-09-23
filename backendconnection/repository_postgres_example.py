"""Adapt these names to YOUR lecture schema. No database is created by this file."""
import os
import psycopg
from psycopg.rows import dict_row

def list_items(category_id):
    with psycopg.connect(os.environ['DATABASE_DSN']) as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            # Bind VALUES. Table/column names here are developer-written SQL.
            cursor.execute('''SELECT i.item_id, i.title, c.category_name
                FROM item i JOIN category c ON c.category_id = i.category_id
                WHERE c.category_id = %s ORDER BY i.title''', (category_id,))
            return cursor.fetchall()

# Add create/update/delete methods when those milestones arrive.
# Validate input in your route; use a fixed WHERE primary_key = %s for changes.
# In a `with connection` block, success commits; an exception rolls back.
