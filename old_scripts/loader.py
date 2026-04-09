"""
loader.py — Lädt die Excel-Datei und gibt die Tabellenblätter als DataFrames zurück.
"""

import os
import pandas as pd
import yaml


def load_config(project_dir: str) -> dict:
    """Lädt die config.yaml aus dem config-Verzeichnis."""
    config_path = os.path.join(project_dir, "config", "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_tabellen(config: dict, project_dir: str) -> dict[str, pd.DataFrame]:
    """
    Lädt alle Tabellenblätter aus der Excel-Datei.

    Validiert, dass die Tabellennamen in der config.yaml mit den
    Blattnamen in der Excel-Datei übereinstimmen.

    Returns:
        tabellen: Dict mit var_name -> DataFrame
    """
    raw_data_dir = os.path.join(project_dir, "data", "raw")
    datei_pfad   = os.path.join(raw_data_dir, config["datei"]["filename"])

    xl = pd.ExcelFile(datei_pfad)

    # Validierung
    config_sheets = set(config["tabellen"].values())
    excel_sheets  = set(xl.sheet_names)
    assert config_sheets == excel_sheets, (
        f"Tabellenname-Konflikt:\n"
        f"  Nur in config:  {config_sheets - excel_sheets}\n"
        f"  Nur in Excel:   {excel_sheets - config_sheets}"
    )

    # Laden
    tabellen = {}
    for var_name, sheet_name in config["tabellen"].items():
        tabellen[var_name] = xl.parse(sheet_name)
        print(f"Geladen: {var_name} → {sheet_name} ({len(tabellen[var_name])} Zeilen)")

    return tabellen
