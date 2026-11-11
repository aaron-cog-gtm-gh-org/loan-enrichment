from pathlib import Path

from db import connect

ROOT = Path(__file__).resolve().parent


def run():
    with connect() as db:
        db.execute("""CREATE OR REPLACE TABLE fx_rates AS
                      SELECT currency, rate::DECIMAL(38,8) AS rate
                      FROM read_csv_auto(?, all_varchar = true)""",
                   [str(ROOT / "data/fx_rates.csv")])
        db.execute("CREATE OR REPLACE TABLE product_map AS SELECT * FROM read_csv_auto(?)",
                   [str(ROOT / "data/product_map.csv")])
        db.execute("""
            CREATE OR REPLACE TABLE enr_loans AS
            SELECT s.* EXCLUDE (balance_usd),
                   round(f.rate * s.balance, 2)::DECIMAL(18,2) AS balance_usd,
                   p.product_name
            FROM stg_loans s
            JOIN fx_rates f ON s.currency = f.currency
            JOIN product_map p ON s.product_code = p.product_code
        """)


if __name__ == "__main__":
    run()
