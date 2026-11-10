# loan-enrichment
Reads: stg_loans and owned data/fx_rates.csv and data/product_map.csv.
Writes: fx_rates, product_map and enr_loans.
Owns: Finance data FX and product enrichment.
Run: pip install -r requirements.txt; make run; make test. Shared DB: $RECON_DB (default ~/lending-demo/lending.duckdb); tables are replaced on each run.
