"""
overview.py — Aufgabe 1: Datenüberblick.

Erzeugt pro Tabelle:
  - uebersicht.png     : Allgemeine Kennzahlen (Zeilen, Spalten, Fehlend, Duplikate)
  - spalten_detail.png : Spaltenweise Qualitätsübersicht
  - head.png           : Erste 10 Zeilen
"""

import os
import pandas as pd
import dataframe_image as dfi
from IPython.display import display


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def berechne_leer_pro_spalte(df: pd.DataFrame) -> pd.Series:
    """
    Zählt leere Strings und Whitespace-only Einträge pro Spalte.

    Annahme: Leere Strings ('') und Whitespace-only Strings (' ')
    sind funktional äquivalent zu fehlenden Werten und werden als
    solche gezählt. Gilt nur für Spalten mit dtype=object.
    """
    leer = pd.Series(0, index=df.columns)
    for col in df.columns:
        if df[col].dtype == "object":
            try:
                leer[col] = (df[col].str.strip() == "").sum()
            except AttributeError:
                pass
    return leer


def berechne_gesamt_fehlend(df: pd.DataFrame) -> pd.Series:
    """Gesamt fehlende Werte pro Spalte: NaN + leer + whitespace."""
    return df.isna().sum() + berechne_leer_pro_spalte(df)


# ── Hauptfunktion ─────────────────────────────────────────────────────────────

def run_overview(tabellen: dict, config: dict, project_dir: str) -> None:
    """
    Erzeugt den Datenüberblick (Aufgabe 1) für alle Tabellenblätter.

    Args:
        tabellen:    Dict mit var_name -> DataFrame (aus loader.py)
        config:      Geladene config.yaml
        project_dir: Projektverzeichnis
    """
    output_dir = os.path.join(project_dir, "output", "datenueberblick")
    os.makedirs(output_dir, exist_ok=True)

    dpi = config["export"]["bilder"]["dpi"]

    for var_name, df in tabellen.items():
        table_name = config["tabellen"][var_name]
        print(f"\n── {table_name} ──")

        _export_uebersicht(df, table_name, output_dir, dpi)
        _export_spalten_detail(df, table_name, output_dir, dpi)
        _export_head(df, table_name, output_dir, dpi)


# ── Private Hilfsfunktionen ───────────────────────────────────────────────────

def _export_uebersicht(
    df: pd.DataFrame,
    table_name: str,
    output_dir: str,
    dpi: int
) -> None:
    """Allgemeine Kennzahlen-Tabelle."""
    total_zellen   = len(df) * len(df.columns)
    nan_gesamt     = int(df.isna().sum().sum())
    leer_gesamt    = int(berechne_leer_pro_spalte(df).sum())
    duplikate      = int(df.duplicated().sum())

    uebersicht = pd.DataFrame({
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
            "—",
            "—",
            f"{nan_gesamt / total_zellen * 100:.1f}%",
            f"{leer_gesamt / total_zellen * 100:.1f}%",
            f"{duplikate / len(df) * 100:.1f}%",
        ],
    })

    styled = uebersicht.style.set_caption(table_name).hide(axis="index")
    display(styled)

    dfi.export(
        styled,
        os.path.join(output_dir, f"{table_name}_uebersicht.png"),
        table_conversion="matplotlib",
        dpi=dpi * 0.5,
    )


def _export_spalten_detail(
    df: pd.DataFrame,
    table_name: str,
    output_dir: str,
    dpi: int
) -> None:
    """Spaltenweise Qualitätsübersicht."""
    gesamt_pro_spalte    = berechne_gesamt_fehlend(df)
    gesamt_fehlend_pct   = gesamt_pro_spalte.sum() / (len(df) * len(df.columns)) * 100

    spalten_detail = pd.DataFrame({
        "Spalte":           df.columns,
        "Datentyp":         df.dtypes.values,
        "Fehlend":          gesamt_pro_spalte.values,
        "% Fehlend":        [f"{x:.1f}%" for x in (gesamt_pro_spalte / len(df) * 100).values],
        "Eindeutige Werte": df.nunique().values,
        "% Eindeutig":      [f"{x:.1f}%" for x in (df.nunique() / len(df) * 100).values],
    })

    styled = (
        spalten_detail.style
        .hide(axis="index")
        .set_caption(
            f"{table_name} — "
            f"Zeilen: {len(df)}, "
            f"Spalten: {len(df.columns)}, "
            f"Fehlend: {gesamt_fehlend_pct:.1f}%, "
            f"Duplizierte Zeilen: {int(df.duplicated().sum())}"
        )
        .map(
            lambda v: "color: red;" if isinstance(v, (int, float)) and v > 0 else "",
            subset=["Fehlend"]
        )
    )

    display(styled)

    dfi.export(
        styled,
        os.path.join(output_dir, f"{table_name}_spalten_detail.png"),
        table_conversion="matplotlib",
        dpi=dpi,
    )


def _export_head(
    df: pd.DataFrame,
    table_name: str,
    output_dir: str,
    dpi: int
) -> None:
    """Erste 10 Zeilen der Tabelle."""
    styled = df.head(10).style.set_caption(f"{table_name} — erste Zeilen")
    display(styled)

    dfi.export(
        styled,
        os.path.join(output_dir, f"{table_name}_head.png"),
        table_conversion="matplotlib",
        dpi=dpi,
    )
