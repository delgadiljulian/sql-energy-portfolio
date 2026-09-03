# SQL Energy Analytics Portfolio

A structured SQL analytics portfolio focusing on the global energy sector, oil and gas markets, power infrastructure, and regulatory filings using SQLite, Python, and official public datasets.

---

## Portfolio Projects

1. [01_texas_houston_energy/](01_texas_houston_energy/)
   - Scope: Texas upstream production, Houston Ship Channel refining and marine terminal hubs, WTI versus Brent crude pricing benchmarks, and orphan well environmental liabilities.
   - Data Sources: Railroad Commission of Texas (RRC) regulatory datasets and U.S. Energy Information Administration (EIA).
   - Core SQL Concepts: Table joins, groupings, aggregate filtering, conditional expressions, common table expressions, and analytical window functions.

2. [02_brazil_presal_energy/](02_brazil_presal_energy/) (Upcoming)
   - Scope: Brazilian offshore pre-salt exploration across the Santos and Campos basins, operator production metrics, and Agencia Nacional do Petroleo (ANP) public data.

3. [03_colombia_energy/](03_colombia_energy/) (Upcoming)
   - Scope: Colombian sedimentary basins including Llanos Orientales and Middle Magdalena Valley, field-level output, and Agencia Nacional de Hidrocarburos (ANH) regulatory data.

---

## Getting Started

To explore the Texas and Houston project:

```bash
cd 01_texas_houston_energy
python run.py
```

Database connection details for DBeaver or database clients:
- Engine: SQLite 3
- Path: 01_texas_houston_energy/data/houston_energy.db
- Query File: 01_texas_houston_energy/queries/complete_queries_log.sql

---

## Technical Stack

- Database Engine: SQLite 3
- Interface: DBeaver Community, Visual Studio Code
- Environment: Python 3.13
- Version Control: Git, GitHub
