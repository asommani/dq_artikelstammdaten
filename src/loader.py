"""
loader.py -- Laedt Config, Rules und Excel-Daten.
"""

import os
import pandas as pd
from .utils import load_yaml


def load_config(project_dir: str) -> dict:
    """Laedt config.yaml."""
    return load_yaml(os.path.join(project_dir, "config", "config.yaml"))


def load_rules(project_dir: str) -> dict:
    """Laedt rules.yaml."""
    return load_yaml(os.path.join(project_dir, "config", "rules.yaml"))


def load_tabellen(config: dict, project_dir: str) -> dict[str, pd.DataFrame]:
    """
    Laedt alle Tabellenblatter aus der Excel-Datei.

    Validiert, dass die Tabellennamen in config.yaml mit den
    Blattnamen in der Excel-Datei uebereinstimmen.

    Returns:
        tabellen: Dict mit var_name -> DataFrame
    """
    datei_pfad = os.path.join(
        project_dir, "data", "raw", config["datei"]["filename"]
    )
    xl = pd.ExcelFile(datei_pfad)

    # Validierung: config vs. Excel
    config_sheets = set(config["tabellen"].values())
    excel_sheets  = set(xl.sheet_names)
    assert config_sheets == excel_sheets, (
        f"Tabellenname-Konflikt:\n"
        f"  Nur in config: {config_sheets - excel_sheets}\n"
        f"  Nur in Excel:  {excel_sheets - config_sheets}"
    )

    tabellen = {}
    for var_name, sheet_name in config["tabellen"].items():
        tabellen[var_name] = xl.parse(sheet_name)
        print(f"Geladen: {var_name} -> {sheet_name} ({len(tabellen[var_name])} Zeilen)")

    return tabellen
