"""Migration: an old DB with UNIQUE(folder, uid) is rebuilt to
UNIQUE(account_id, folder, uid), preserving rows and remapping legacy
account_id 0 to the sole account (so multi-account sync neither collides nor
duplicates)."""

from __future__ import annotations

import sqlite3


async def test_rebuild_email_message_migration(data_dir):
    from app import config, db

    dbp = config.db_path()
    con = sqlite3.connect(dbp)
    con.execute(
        """CREATE TABLE email_message (
          id INTEGER PRIMARY KEY, uid TEXT, folder TEXT, from_address TEXT,
          to_addresses TEXT, subject TEXT, body_text TEXT, date TIMESTAMP,
          translated_text TEXT, detected_lang TEXT, account_id INTEGER DEFAULT 0,
          CONSTRAINT uq_email_folder_uid UNIQUE (folder, uid))"""
    )
    con.execute(
        "INSERT INTO email_message (uid, folder, from_address, to_addresses, subject, "
        "body_text, date, account_id) VALUES "
        "('1700055660','INBOX','hr@corp.com','me@163.com','confirmed','',"
        "'2026-07-02 21:05:53',0)"
    )
    con.execute(
        "CREATE TABLE account (id INTEGER PRIMARY KEY, host TEXT, port INT, use_ssl INT, "
        "username TEXT, credential_key TEXT, display_name TEXT, uid_validity INT, "
        "last_sync_at TEXT)"
    )
    con.execute("INSERT INTO account (id, username) VALUES (1, 'me@163.com')")
    con.commit()
    con.close()

    await db.reset_engine()
    await db.init_db()

    con = sqlite3.connect(dbp)
    try:
        # The unique constraint is now (account_id, folder, uid).
        unique_sets = []
        for idx in con.execute("PRAGMA index_list(email_message)"):
            if idx[2] == 1:  # unique
                unique_sets.append({r[2] for r in con.execute(f"PRAGMA index_info('{idx[1]}')")})
        assert {"account_id", "folder", "uid"} in unique_sets

        # Row preserved, legacy account_id 0 remapped to the sole account (1).
        row = con.execute(
            "SELECT account_id, uid, subject FROM email_message WHERE uid='1700055660'"
        ).fetchone()
        assert row == (1, "1700055660", "confirmed")
        assert con.execute("SELECT count(*) FROM email_message").fetchone()[0] == 1

        # The job-pipeline screen column was added and defaults to 0 (unscreened).
        cols = {r[1] for r in con.execute("PRAGMA table_info(email_message)")}
        assert "job_screened" in cols
        assert con.execute(
            "SELECT job_screened FROM email_message WHERE uid='1700055660'"
        ).fetchone()[0] == 0
    finally:
        con.close()
        await db.reset_engine()
