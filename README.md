# Datenqualitätsanalyse – Artikelstammdaten

A lightweight, extensible data quality framework built in Python.  
Rules are defined declaratively in YAML — adding a new domain requires no changes to the engine.

---

## Project Structure

```
dq_artikelstammdaten/
config/
├── config.yaml          # paths, sheet names, export settings
└── rules.yaml           # all business/analysis rules
├── data/
│   └── raw/                           # Place input files here (not tracked by git)
├── docs/
|    └── annahmen.md                   # Assumtions list
src/
├── __init__.py
├── loader.py            # loads data + both configs
├── overview.py        # Aufgabe 1a: Datenüberblick
├── normalization.py   # Aufgabe 1b: Normalformanalyse
├── kpi.py               # Aufgabe 2
└── reporter.py          # Aufgabe 3
|
|-- output/
|    └── 2026-04-08_14-36-27/   # each run gets its own folder
|        ├── datenueberblick/
|        └── normalisierungsanalyse/
├── tests/
│   └── 
├── run_analysis.py          # automated, repeatable: overview + KPIs + dashboard
├── normalization_analysis.py  # one-time schema audit, exploratory
├── missing: streamlit_app.py                   # Interactive dashboard
├── requirements.txt
└── .gitignore
```

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/dq_artikelstammdaten.git
cd dq_artikelstammdaten
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Place the input files

- Copy the provided Excel file into `data/raw/`:
  ```
  data/raw/Recruiting_Aufgabe_Data_Analyst_08_25.xlsx
  ```
- Copy the task brief PDF into `docs/`:
  ```
  docs/Recruiting_Aufgabe_Data_Analyst_08_25.pdf
  ```

These files are excluded from version control (see `.gitignore`).

---

## Usage

### Run the analysis (CLI)

Produces `output/dq_report.xlsx` and `output/dq_dashboard.png`:

```bash
python run_analysis.py \
  --config config/rules_artikelstammdaten.yaml \
  --data   data/raw/Recruiting_Aufgabe_Data_Analyst_08_25.xlsx \
  --output output/
```

### Launch the interactive dashboard

```bash
streamlit run streamlit_app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.  
The dashboard is domain-agnostic: use the file picker to load any `output/` folder.

---

## Extending to a new domain

1. Create a new rule config: `config/rules_<domain>.yaml`
2. Place the corresponding input file in `data/raw/`
3. Run `run_analysis.py` with the new `--config` and `--data` arguments
4. The dashboard loads the new results without any code changes

---

## Requirements

See `requirements.txt`. Key dependencies:

- `pandas` — data loading and manipulation
- `openpyxl` — Excel I/O
- `pyyaml` — YAML config parsing
- `matplotlib` / `seaborn` — static chart export
- `streamlit` — interactive dashboard
- `plotly` — interactive charts within Streamlit

---

## Notes

- Raw data and task documents are intentionally excluded from version control.  
  See `.gitignore` and the setup instructions above.
- All assumptions made during the analysis are documented in `docs/assumptions.md`  
  (to be created during the analysis).
