#%%
"""
utils.py -- Gemeinsame Hilfsfunktionen fuer Pfade und Datenqualitaet.
"""

import os
import yaml
import pandas as pd
from datetime import datetime
import contextlib
import io
#%%
# ── Pfade ─────────────────────────────────────────────────────

def get_project_dir() -> str:
    """
    Gibt das Projektverzeichnis zurueck.

    Annahme: utils.py liegt in src/, daher zwei Ebenen hoch.
    Nur aus src/-Modulen aufrufen (loader.py, overview.py, kpi.py etc.).
    Nicht aus run_analysis.py aufrufen -- dort stattdessen direkt:
        project_dir = os.path.dirname(os.path.abspath(__file__))
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_run_output_dir(project_dir: str) -> str:
    """
    Erstellt einen timestamped Output-Ordner fuer diesen Run.
    z.B. output/2026-04-08_14-36-27/
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    #path = os.path.join(project_dir, "output", timestamp)
    path = os.path.join(project_dir, "output", 'now')  # for easier access during development

    os.makedirs(path, exist_ok=True)
    return path


def get_output_dir(run_dir: str, subfolder: str = "") -> str:
    """Erstellt und gibt einen Unterordner im aktuellen Run-Verzeichnis zurueck."""
    path = os.path.join(run_dir, subfolder) if subfolder else run_dir
    os.makedirs(path, exist_ok=True)
    return path


def load_yaml(path: str) -> dict:
    """Laedt eine YAML-Datei und gibt sie als Dictionary zurueck."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


# ── Fehlende Werte ────────────────────────────────────────────

def leer_pro_spalte(df: pd.DataFrame) -> pd.Series:
    """
    Zaehlt leere Strings ('') und Whitespace-only Strings (' ') pro Spalte.

    Annahme (siehe Annahmen.md): Leere und Whitespace-Strings sind funktional
    aequivalent zu NaN und werden als fehlende Werte gezaehlt.
    Gilt nur fuer Spalten mit dtype=object.
    """
    result = pd.Series(0, index=df.columns)
    for col in df.columns:
        if df[col].dtype == "object":
            try:
                result[col] = (df[col].str.strip() == "").sum()
            except AttributeError:
                pass
    return result


def fehlend_pro_spalte(df: pd.DataFrame) -> pd.Series:
    """Gesamt fehlende Werte pro Spalte: NaN + leer + whitespace."""
    return df.isna().sum() + leer_pro_spalte(df)


def fehlend_gesamt(df: pd.DataFrame) -> int:
    """Summe aller fehlenden Werte ueber alle Spalten."""
    return int(fehlend_pro_spalte(df).sum())
