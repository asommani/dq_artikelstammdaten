# Data Quality Analysis – Article Master Data

A lightweight, extensible data quality framework built in Python.

The solution is **config-driven**: all business rules are defined declaratively in YAML.  
Adding new domains or checks requires **no changes to the core engine**.

---

## Overview

This project implements a **scalable and reproducible data quality analysis pipeline** for article master data of a (fictitious) retail company.

It was developed as part of a **Data Analyst / Data Quality Manager case study**.

The pipeline:
- analyzes multiple data domains
- computes standardized KPIs
- detects inconsistencies and data issues
- generates a dashboard for decision-making

---

## Business Context

Poor data quality has direct operational impact:

- Incorrect product information → **legal risks**
- Wrong dimensions → **logistics errors**
- Inconsistent data → **customer complaints and support overhead**

The company lacks a standardized way to measure and monitor data quality.

This project introduces a **repeatable, scalable approach** to data quality management.

---

## Key Features

- Config-driven architecture (`config.yaml`, `rules.yaml`)
- Automated KPI computation
- Modular pipeline (overview → KPIs → reporter → dashboard)
- Reproducible outputs
- Clear separation of logic and business rules

---

## KPIs and Data Quality Analysis 

### Core KPIs (as defined in the task)

#### Completeness
- Share of required fields without missing values

#### Uniqueness
- Article number uniqueness
- GTIN uniqueness

#### Consistency
- Consistency of dimensions based on comparison between Grunddaten and Werksdaten (deviation > 10% classified as inconsistent)
- Unit consistency of dimensions

### Additional Data Quality Checks
#### Supporting Checks (used in the dashboard)
- Price validation (sentinel values, currency consistency)
- Reference integrity checks
- Werksdaten conflict detection 

#### Diagnostics and Additional Analysis (to support findings and recommendations)
- Flagging function for 1NF atomicity check
- Plausibility checks on physical measurements (e.g. negative or zero dimensions)
- Detection of articles in Grunddaten without corresponding Werksdaten
- GTIN format validation (EAN-13)
- Controlled vocabulary validation

---

## Project Structure

```
dq_artikelstammdaten/
├── config/          # configuration & business rules
├── src/             # modular analysis logic
├── data/raw/        # input data (not tracked)
├── output/          # generated results (CSVs, dashboard) (not tracked)
├── diagnostics/     # exploratory scripts
└── run_analysis.py
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

### 4. Place the input file

Copy the Excel file into:

```
data/raw/<filename>.xlsx
```

The raw data is excluded from version control.

---

## Usage

Run the full analysis pipeline:

```bash
python run_analysis.py
```

## Output

- KPI and reporting results (`.csv`)
- Interactive dashboard (`.html`)
- Dashboard export (`.png`)

The output data is excluded from version control.

---


## Configuration

### `config.yaml`
Defines:
- file paths
- sheet names
- export settings
- runtime flags

### `rules.yaml`
Defines:
- KPI logic
- validation rules
- thresholds
- controlled vocabularies

This separation allows adapting business rules without changing python code.

---

## Extending to a New Domain

1. Modify `config.yaml` and `rules.yaml`
2. Place new input data in `data/raw/`
3. Run `run_analysis.py`

The pipeline automatically applies the new rules.

---

## Requirements

See `requirements.txt`.

Core dependencies:
- pandas
- numpy
- PyYAML
- openpyxl
- plotly
- kaleido (required for dashboard PNG export)

Optional:
- dataframe_image (only for PNG export of tables)

---

## Documentation and assumtions

All assumptions made during the analysis, as well as the methodological decisions and rationale behind key design choices are documented in:


```
annahmen_methodik.md
```

---

## Language Note

This project was developed for a German case study.  
Business terminology follows the original dataset (e.g. *Grunddaten*, *Werksdaten*).
