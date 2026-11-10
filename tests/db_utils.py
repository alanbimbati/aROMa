from sqlalchemy import text


def truncate(session, *tables):
    """Empty tables with plain DELETEs: TRUNCATE ... CASCADE exists only on PostgreSQL, the tests run on SQLite."""
    for table in tables:
        session.execute(text(f"DELETE FROM {table}"))
