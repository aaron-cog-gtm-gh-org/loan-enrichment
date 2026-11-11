import argparse
import csv
from decimal import Decimal, ROUND_HALF_UP
import importlib.util
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def check_fx(pipeline_path=ROOT / "pipeline.py"):
    rng = random.Random(1610847)
    with (ROOT / "data/fx_rates.csv").open() as source:
        rates = {row["currency"]: row["rate"] for row in csv.DictReader(source)}
    cases = []
    for currency in rates:
        for balance in ("0", "0.01", "-0.01", "1000000000000.00", "-1000000000000.00"):
            cases.append((currency, balance))
    cases.append(("EUR", "473157.56"))
    for index, (balance, rate) in enumerate([
        ("0.01", "1.50000000"), ("-0.01", "1.50000000"),
        ("0.01", "1.49999999"), ("0.01", "1.50000001"),
        ("1.00", "1.00500000"), ("-1.00", "1.00500000"),
        ("1000000000000.00", "1.08470000"),
    ]):
        currency = f"EDGE{index}"
        rates[currency] = rate
        cases.append((currency, balance))
    for index in range(600):
        currency = f"R{index}"
        rates[currency] = f"{Decimal(rng.randint(1, 250000000)) / Decimal(100000000):.8f}"
        balance = Decimal(rng.randint(-100000000000000, 100000000000000)) / 100
        cases.append((currency, str(balance)))
        cases.append((rng.choice(("USD", "GBP", "EUR")), str(balance)))

    sys.path.insert(0, str(ROOT))
    try:
        spec = importlib.util.spec_from_file_location("fx_pipeline_under_test", pipeline_path)
        pipeline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pipeline)
    finally:
        sys.path.pop(0)

    failures = []
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "data").mkdir()
        shutil.copy(ROOT / "data/product_map.csv", root / "data/product_map.csv")
        with (root / "data/fx_rates.csv").open("w", newline="") as target:
            writer = csv.writer(target)
            writer.writerow(("currency", "rate"))
            writer.writerows(rates.items())
        path = root / "fuzz.duckdb"
        with duckdb.connect(str(path)) as db:
            assert db.execute("SELECT (0.005::DECIMAL(38,8))::DECIMAL(18,2), (-0.005::DECIMAL(38,8))::DECIMAL(18,2)").fetchone() == (Decimal("0.01"), Decimal("-0.01"))
            db.execute("CREATE TABLE stg_loans (loan_id VARCHAR, currency VARCHAR, product_code VARCHAR, balance DECIMAL(18,2), balance_usd DECIMAL(18,2))")
            db.executemany("INSERT INTO stg_loans VALUES (?, ?, 'MTG', ?, 0)",
                           [(str(i), currency, Decimal(balance)) for i, (currency, balance) in enumerate(cases)])
        previous_db = os.environ.get("RECON_DB")
        previous_root = pipeline.ROOT
        os.environ["RECON_DB"] = str(path)
        pipeline.ROOT = root
        try:
            pipeline.run()
        finally:
            pipeline.ROOT = previous_root
            if previous_db is None:
                os.environ.pop("RECON_DB", None)
            else:
                os.environ["RECON_DB"] = previous_db
        with duckdb.connect(str(path)) as db:
            actual = dict(db.execute("SELECT loan_id, balance_usd FROM enr_loans").fetchall())
        assert len(actual) == len(cases)
        for index, (currency, balance) in enumerate(cases):
            expected = (Decimal(balance) * Decimal(rates[currency])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if actual[str(index)] != expected:
                failures.append(f"{currency}: {balance} * {rates[currency]}: expected {expected}, got {actual[str(index)]}")
    for failure in failures[:5]:
        print(failure)
    print(f"inputs tested: {len(cases)}, failures: {len(failures)}")
    return failures


def test_fuzz_fx():
    assert not check_fx()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline", type=Path, default=ROOT / "pipeline.py")
    args = parser.parse_args()
    sys.exit(bool(check_fx(args.pipeline)))
