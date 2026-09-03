# 🛢️ SQL Energy Analytics Portfolio

A production-grade SQL analytics portfolio focusing on the global energy sector, oil & gas markets, power grids, and downstream infrastructure using SQLite, Python, and official regulatory data.

---

## 🗂️ Portfolio Projects

1. **[`01_texas_houston_energy/`](01_texas_houston_energy/)**  
   * **Scope**: Texas Oil & Gas Upstream, Houston Ship Channel refining & maritime hubs, WTI vs Brent market dynamics, and environmental plugging liabilities.
   * **Data Sources**: Official Railroad Commission of Texas (RRC) regulatory filings and U.S. Energy Information Administration (EIA).
   * **Key Techniques**: Complex `JOIN`s, `GROUP BY`, `HAVING`, Conditional `CASE WHEN`, Common Table Expressions (`WITH`), and Window Functions (`ROW_NUMBER() OVER (PARTITION BY ...)`).

2. **[`02_brazil_presal_energy/`](02_brazil_presal_energy/)** *(Upcoming)*  
   * **Scope**: Brazil Pre-Salt deepwater exploration (Santos and Campos basins), Petrobras operational metrics, and ANP open data.

3. **[`03_colombia_energy_analytics/`](03_colombia_energy_analytics/)** *(Upcoming)*  
   * **Scope**: Colombian hydrocarbon basins (Llanos Orientales, Middle Magdalena Valley), Ecopetrol production assets, and ANH regulatory data.

---

## 🚀 Quick Start

To explore the Texas & Houston project:

```bash
cd 01_texas_houston_energy
# Run SQL queries using the CLI runner:
python run.py

# Or open the SQLite database in DBeaver / VS Code:
# Path: 01_texas_houston_energy/data/houston_energy.db
```

---

## 🛠️ Tech Stack & Tools
* **SQL Engine**: SQLite 3
* **GUI / Query Client**: DBeaver Community / VS Code SQLite Viewer
* **Scripting & Data Pipelines**: Python 3.13 (Standard Library + Data Processing)
* **Version Control**: Git & GitHub
