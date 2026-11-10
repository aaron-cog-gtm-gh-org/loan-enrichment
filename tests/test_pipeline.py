import duckdb
import pytest

from pipeline import run


@pytest.fixture
def database(tmp_path, monkeypatch):
    path = tmp_path / "test.duckdb"
    monkeypatch.setenv("RECON_DB", str(path))
    with duckdb.connect(str(path)) as db:
        db.execute("""
            CREATE TABLE stg_loans AS SELECT 'L1' AS loan_id, 'USD' AS currency,
                'MTG' AS product_code, 125.25::DECIMAL(18,2) AS balance,
                125.25::DECIMAL(18,2) AS balance_usd
        """)
    return path


def test_usd_product_and_idempotency(database):
    run()
    with duckdb.connect(str(database)) as db:
        first = db.execute("SELECT * FROM enr_loans").fetchall()
        assert db.execute("SELECT balance_usd, product_name FROM enr_loans").fetchone() == (125.25, "Mortgage")
        assert db.execute("SELECT count(*) FROM fx_rates").fetchone()[0] == 3
    run()
    with duckdb.connect(str(database)) as db:
        assert db.execute("SELECT * FROM enr_loans").fetchall() == first


def test_empty_input(database):
    with duckdb.connect(str(database)) as db:
        db.execute("DELETE FROM stg_loans")
    run()
    with duckdb.connect(str(database)) as db:
        assert db.execute("SELECT count(*) FROM enr_loans").fetchone()[0] == 0


def test_missing_upstream(database):
    with duckdb.connect(str(database)) as db:
        db.execute("DROP TABLE stg_loans")
    with pytest.raises(duckdb.CatalogException):
        run()
