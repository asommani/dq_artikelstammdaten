#%%
"""
dev_kpis.py -- Entwicklungsskript fuer Aufgabe 2: KPI-Berechnung.

Aufruf:
    python dev_kpis.py
"""

import os
import sys

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from src.kpi import run_konsistenz_einheit_masse, run_vollstaendigkeit, run_eindeutigkeit, run_konsistenz_masse
from src.loader import load_config, load_rules, load_tabellen
from src.utils import get_run_output_dir, get_output_dir
import dataframe_image as dfi


from IPython.display import display
IN_NOTEBOOK = True
config   = load_config(project_dir)
rules    = load_rules(project_dir)
tabellen = load_tabellen(config, project_dir)

#%%
# ── Vollstaendigkeit ────────────────────────────────────────
print("\n" + "=" * 65)
print("KPI: Vollstaendigkeit Pflichtfelder")
print("=" * 65)

run_dir = get_run_output_dir(project_dir)

#%%
rules
#%%
grunddaten_name = list(rules["pflichtfelder"].keys())[0]
vollstaendigkeit_results = run_vollstaendigkeit(tabellen, rules, config, run_dir)

list(vollstaendigkeit_results.values())[0]
eindeutigkeit_results = run_eindeutigkeit(tabellen, rules, config, run_dir)

list(eindeutigkeit_results.values())[0]
# %%
konsistenz_masse_result   = run_konsistenz_masse(tabellen, rules, config, run_dir)
konsistenz_masse_result
#%%
konsistenz_einheit_masse = run_konsistenz_einheit_masse(tabellen, rules, config, run_dir)
#%%
# import pandas as pd

# # ── Konsistenz: Einheit Masse ─────────────────────────────────

# def check_konsistenz_einheit_masse(
#     tabellen: dict,
#     checks:   list[dict],
#     rules:    dict,
# ) -> pd.DataFrame:
#     rows = []
#     for check in checks:
#         df      = tabellen[check["tabelle"]]
#         spalte  = check["spalte"]
#         gueltig = rules
#         for key in check["gueltige_werte"].split("."):
#             gueltig = gueltig[key]

#         col          = df[spalte].replace(r"^\s*$", pd.NA, regex=True)
#         n_gesamt     = len(col)
#         n_fehlend    = int(col.isnull().sum())
#         col_present  = col.dropna()
#         mask_invalid = ~col_present.isin(gueltig)
#         n_invalid    = int(mask_invalid.sum())
#         n_valid      = n_gesamt - n_fehlend - n_invalid

#         rows.append({
#             "tabelle":          check["tabelle"],
#             "spalte":           spalte,
#             "gueltig":          ", ".join(gueltig),
#             "gesamt":           n_gesamt,
#             "fehlend":          n_fehlend,
#             "valid":            n_valid,
#             "valid_rate":       n_valid   / n_gesamt if n_gesamt > 0 else None,
#             "invalid":          n_invalid,
#             "invalid_rate":     n_invalid / n_gesamt if n_gesamt > 0 else None,
#             "vorhandene_werte": col_present.value_counts().to_dict(),
#             "invalid_werte":    col_present[mask_invalid].unique().tolist(),
#             "einheitlich":      n_invalid == 0 and n_fehlend == 0,
#         })
#     return pd.DataFrame(rows)

# def _style_konsistenz_einheit_masse(df_result: pd.DataFrame) -> pd.Styler:
#     return (
#         df_result.style
#         .hide(axis="index")
#         .set_caption("Konsistenz – Einheitlichkeit der Maßeinheiten")
#         .format({"invalid_rate": "{:.1%}", "valid_rate": "{:.1%}"})
#     )


# def run_konsistenz_einheit_masse(tabellen: dict, rules: dict, config: dict, run_dir: str) -> pd.DataFrame:
#     output_dir = get_output_dir(run_dir, "kpis")
#     dpi        = config["export"]["dpi"]

#     result = check_konsistenz_einheit_masse(
#         tabellen = tabellen,
#         checks   = rules["konsistenz_einheit_masse"],
#         rules    = rules,
#     )

#     # CSV
#     csv_path = os.path.join(output_dir, "konsistenz_einheit_masse.csv")
#     result.to_csv(csv_path, index=False)
#     print(f"  Gespeichert: {os.path.basename(csv_path)}")

#     # PNG
#     styled   = _style_konsistenz_einheit_masse(result)
#     png_path = os.path.join(output_dir, "konsistenz_einheit_masse.png")
#     dfi.export(styled, png_path, table_conversion="matplotlib", dpi=dpi)
#     print(f"  Gespeichert: {os.path.basename(png_path)}")

#     if IN_NOTEBOOK:
#         display(styled)

#     return result

# %%
result = run_konsistenz_einheit_masse(tabellen, rules, config, run_dir)
# %%
result
# %%
