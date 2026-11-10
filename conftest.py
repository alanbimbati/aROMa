"""Makes `pytest` behave like run_tests.py: SQLite test database, every model's table created up front."""
import importlib
import os
import pkgutil
import tempfile

import pytest

os.environ.setdefault('TEST_DB', '1')
os.environ.setdefault('DB_TYPE', 'sqlite')
os.environ.setdefault('TEST', '1')
# A throwaway database per run, so rows left by a previous run or another file never leak in.
if os.environ.get('DB_TYPE') == 'sqlite' and not os.environ.get('SQLITE_PATH'):
    os.environ['SQLITE_PATH'] = os.path.join(tempfile.mkdtemp(prefix='aroma-test-'), 'test_points.db')


# Static game catalogue seeded from data/*.csv by db_setup: tests read it, none owns it.
CATALOG_TABLES = {'refined_materials', 'resources', 'equipment', 'mounts'}


def pytest_configure(config):
    import models
    from database import Database
    for module in pkgutil.iter_modules(models.__path__):
        if not module.name.startswith('_'):
            importlib.import_module(f"models.{module.name}")
    db = Database()
    db.create_all_tables()
    import db_setup
    for seed in (db_setup.seed_refined_materials, db_setup.seed_resources, db_setup.seed_equipment, db_setup.seed_mounts):
        seed(db)


@pytest.fixture(autouse=True, scope='module')
def _empty_database_per_module():
    """Every test file starts on empty tables: files seed their own rows and none depends on another's leftovers."""
    import gc
    from database import Base, Database
    gc.collect()  # a session a previous file leaked holds its write lock until it is collected
    engine = Database().engine
    if engine.dialect.name != 'sqlite':
        # Never empty a real database: on PostgreSQL the tests run on whatever is there, as before.
        yield
        return
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            if table.name in CATALOG_TABLES:
                continue
            conn.execute(table.delete())
    yield
