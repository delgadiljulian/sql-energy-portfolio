# Texas & Houston Energy Analytics with SQL

A professional SQL analytics project powered by SQLite, analyzing Texas energy infrastructure, crude oil pricing benchmarks (WTI vs Brent), refining hubs, and upstream wells data.

---

## 📌 Analytical Capabilities

- **Texas Crude Oil Production**: Historical and monthly trends from the U.S. Energy Information Administration (EIA).
- **Crude Oil Market Benchmarks**: Daily spot prices for WTI (West Texas Intermediate) and Brent, plus the calculated Brent-WTI spread.
- **Gulf Coast Refining Capacity**: Atmospheric crude oil distillation and downstream capacity from the EIA-820 refinery report across Texas refining districts.
- **Upstream Wells Analysis**: Well distribution, technical depths, county-level production trends, and environmental plugging liabilities (*Orphan Wells*) from Railroad Commission of Texas (RRC) regulatory filings.

---

## 🚀 Quick Start

Run SQL queries directly using the Python CLI runner:

```powershell
# Run the master queries log:
python run.py

# Run an ad-hoc query directly from terminal:
python run.py "SELECT condado, COUNT(*) AS total_wells FROM pozos_texas GROUP BY condado ORDER BY total_wells DESC LIMIT 5;"

# Run the test suite:
python -m unittest discover tests
```

Or connect directly via **DBeaver** or **VS Code SQLite Viewer**:
* Database Path: `data/houston_energy.db`
* Queries: `queries/complete_queries_log.sql`

---

## 📁 Directory Structure

- `queries/`: Documented SQL analytical queries (`complete_queries_log.sql`).
- `data/`:
  - `houston_energy.db`: SQLite database containing indexed tables and analytical views.
  - `raw/`: Raw official source datasets (EIA, RRC, Port of Houston).
- `scripts/`: Data ingestion, validation, and pipeline scripts (`build_database.py`, `validate_database.py`, etc.).
- `docs/`: Technical data dictionary (`DATA_DICTIONARY.md`), methodology, and source documentation (`SOURCES.md`).
- `outputs/`: Data validation reports (`VALIDATION.md`).
- `tests/`: Automated integration and unit tests (`test_project.py`).
