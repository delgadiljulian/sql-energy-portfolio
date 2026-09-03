# Texas and Houston Energy Analytics

An applied SQL analytics project using SQLite to analyze Texas energy infrastructure, crude oil pricing benchmarks, refining capacity, and upstream well records.

---

## Analytical Scope

- Texas Crude Oil Production: Monthly and annual volumetric trends reported by the U.S. Energy Information Administration (EIA).
- Crude Oil Market Benchmarks: Historical daily spot prices for West Texas Intermediate (WTI) and Brent, including the calculated price differential.
- Gulf Coast Refining Capacity: Atmospheric distillation and secondary unit processing capacities from the EIA-820 refinery survey.
- Upstream Well Inventory: Regulatory records, technical depths, geographic distribution, and inactive well plugging calculations from the Railroad Commission of Texas (RRC).

---

## Execution and Interface

Run analytical scripts through the command line runner:

```powershell
python run.py
```

Database connection configuration for external SQL clients:
- Database File: data/houston_energy.db
- Query File: queries/complete_queries_log.sql

---

## Project Structure

- queries/: Prepared SQL analytical scripts.
- data/: Structured SQLite database file and raw regulatory source files.
- scripts/: Data pipeline, ingestion, and validation scripts.
- docs/: Technical data dictionary and methodology documentation.
- outputs/: Verification and data quality reports.
- tests/: Test suite for schema consistency and query validation.
