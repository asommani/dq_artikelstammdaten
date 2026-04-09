"""
overview.py -- Aufgabe 1: Datenueberblick.

Erzeugt pro Tabelle:
  - {name}_uebersicht.png     : Allgemeine Kennzahlen
  - {name}_spalten_detail.png : Spaltenweise Qualitaetsuebersicht
  - {name}_head.png           : Erste 10 Zeilen

Computation and rendering are separated:
  - compute_*() functions return plain DataFrames (testable, notebook-friendly)
  - run_overview() renders and saves to PNG
"""

import os
import pandas as pd
import dataframe_image as dfi
from .utils import fehlend_pro_spalte, get_output_dir
import re
# display() only if running in a notebook
try:
    from IPython.display import display
    IN_NOTEBOOK = True
except ImportError:
    IN_NOTEBOOK = False


# ── Computation ───────────────────────────────────────────────

def compute_uebersicht(df: pd.DataFrame) -> pd.DataFrame:
    """Berechnet allgemeine Kennzahlen fuer eine Tabelle."""
    total_zellen = len(df) * len(df.columns)
    nan_gesamt   = int(df.isna().sum().sum())

    leer_gesamt = 0
    for col in df.columns:
        if df[col].dtype == "object":
            try:
                leer_gesamt += int((df[col].str.strip() == "").sum())
            except AttributeError:
                pass

    duplikate = int(df.duplicated().sum())

    return pd.DataFrame({
        "Merkmal": [
            "Zeilen",
            "Spalten",
            "NaN",
            "Leer / Whitespace",
            "Duplizierte Zeilen",
        ],
        "Wert": [
            len(df),
            len(df.columns),
            nan_gesamt,
            leer_gesamt,
            duplikate,
        ],
        "Prozent": [
            "-",
            "-",
            f"{nan_gesamt / total_zellen * 100:.1f}%",
            f"{leer_gesamt / total_zellen * 100:.1f}%",
            f"{duplikate / len(df) * 100:.1f}%",
        ],
    })


def compute_spalten_detail(df: pd.DataFrame) -> pd.DataFrame:
    """Berechnet spaltenweise Qualitaetskennzahlen."""
    gesamt = fehlend_pro_spalte(df)

    return pd.DataFrame({
        "Spalte":           df.columns,
        "Datentyp":         df.dtypes.values,
        "Fehlend":          gesamt.values,
        "% Fehlend":        [f"{x:.1f}%" for x in (gesamt / len(df) * 100).values],
        "Eindeutige Werte": df.nunique().values,
        "% Eindeutig":      [f"{x:.1f}%" for x in (df.nunique() / len(df) * 100).values],
    })


# ── Rendering ─────────────────────────────────────────────────

def _style_uebersicht(df_uebersicht: pd.DataFrame, table_name: str):
    return df_uebersicht.style.hide(axis="index").set_caption(table_name)


def _style_spalten_detail(df_detail: pd.DataFrame, df_orig: pd.DataFrame, table_name: str):
    gesamt_pct = (
        fehlend_pro_spalte(df_orig).sum()
        / (len(df_orig) * len(df_orig.columns))
        * 100
    )
    caption = (
        f"{table_name} -- "
        f"Zeilen: {len(df_orig)}, "
        f"Spalten: {len(df_orig.columns)}, "
        f"Fehlend: {gesamt_pct:.1f}%, "
        f"Duplizierte Zeilen: {int(df_orig.duplicated().sum())}"
    )
    return (
        df_detail.style
        .hide(axis="index")
        .set_caption(caption)
        .map(
            lambda v: "color: red;" if isinstance(v, (int, float)) and v > 0 else "",
            subset=["Fehlend"]
        )
    )


def _export(styled, path: str, dpi: int) -> None:
    if IN_NOTEBOOK:
        display(styled)
    dfi.export(styled, path, table_conversion="matplotlib", dpi=dpi)
    print(f"  Gespeichert: {os.path.basename(path)}")

# ── Hauptfunktion ─────────────────────────────────────────────

def run_overview(tabellen: dict, config: dict, run_dir: str) -> None:
    """
    Erzeugt den Datenueberblick (Aufgabe 1) fuer alle Tabellenblatter.

    Args:
        tabellen: Dict var_name -> DataFrame (aus loader.py)
        config:   Geladene config.yaml
        run_dir:  Timestamped output folder fuer diesen Run
    """
    output_dir = get_output_dir(run_dir, "datenueberblick")
    dpi        = config["export"]["dpi"]

    for var_name, df in tabellen.items():
        table_name = config["tabellen"][var_name]
        print(f"\n-- {table_name} --")

        # Uebersicht
        uebersicht = compute_uebersicht(df)
        _export(
            _style_uebersicht(uebersicht, table_name),
            os.path.join(output_dir, f"{var_name}_uebersicht.png"),
            dpi=int(dpi * 0.5),
        )

        # Spalten-Detail
        spalten_detail = compute_spalten_detail(df)
        _export(
            _style_spalten_detail(spalten_detail, df, table_name),
            os.path.join(output_dir, f"{var_name}_spalten_detail.png"),
            dpi=dpi,
        )

        # Head
        _export(
            df.head(10).style.set_caption(f"{table_name} -- erste Zeilen"),
            os.path.join(output_dir, f"{var_name}_head.png"),
            dpi=dpi,
        )
