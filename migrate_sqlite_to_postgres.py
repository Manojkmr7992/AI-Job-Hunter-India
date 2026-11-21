"""One-time, non-destructive migration. Run with JOB_HUNTER_DB=postgres."""
import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from sqlalchemy import text
from core import DB_PATH
from postgres_store import engine, pg_init_db, postgres_enabled


def migrate(apply=False):
    if not postgres_enabled():
        raise RuntimeError('Set JOB_HUNTER_DB=postgres in .env first')
    if not DB_PATH.is_file():
        raise FileNotFoundError(DB_PATH)
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = [dict(row) for row in db.execute('SELECT * FROM jobs ORDER BY id')]
    pg_init_db()
    with engine().connect() as conn:
        existing = conn.execute(text('SELECT COUNT(*) FROM jobs')).scalar_one()
    print(f'SQLite rows: {len(rows)} | PostgreSQL rows before: {existing}')
    if not apply:
        print('DRY RUN ONLY. To migrate, rerun with --apply')
        return
    backup = DB_PATH.with_name('jobs.backup.' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.sqlite3')
    shutil.copy2(DB_PATH, backup)
    print(f'SQLite backup: {backup}')
    with engine().begin() as conn:
        for row in rows:
            conn.execute(text("""INSERT INTO jobs(id,url,title,company,location,country,work_mode,status)
                VALUES (:id,:url,:title,:company,:location,:country,:work_mode,:status)
                ON CONFLICT(url) DO UPDATE SET
                title=excluded.title, company=excluded.company,
                location=excluded.location, country=excluded.country,
                work_mode=excluded.work_mode, status=excluded.status"""),row)
        conn.execute(text("""SELECT setval(pg_get_serial_sequence('jobs','id'),
            GREATEST(COALESCE((SELECT MAX(id) FROM jobs),0),1),
            EXISTS(SELECT 1 FROM jobs))"""))
    with engine().connect() as conn:
        missing = conn.execute(text("""SELECT COUNT(*) FROM (SELECT url FROM jobs WHERE url = ANY(:urls)) t"""), {'urls':[r['url'] for r in rows]}).scalar_one() if rows else 0
        after = conn.execute(text('SELECT COUNT(*) FROM jobs')).scalar_one()
    if missing != len(rows):
        raise RuntimeError(f'Migration verification failed: {missing} of {len(rows)} source URLs found')
    print(f'Verified: {missing}/{len(rows)} SQLite job URLs in PostgreSQL; PostgreSQL total: {after}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply',action='store_true')
    migrate(parser.parse_args().apply)
