#%%
"""
run_analysis.py -- CLI-Einstiegspunkt fuer die Datenqualitaetsanalyse.

Aufruf:
    python run_analysis.py

Fuehrt alle Aufgaben sequenziell aus:
    Aufgabe 1 -- Datenueberblick  (overview.py)
    Aufgabe 2 -- KPI-Berechnung   (kpi.py)       [noch nicht implementiert]
    Aufgabe 3 -- Dashboard        (dashboard.py)  [noch nicht implementiert]
"""

import os

# run_analysis.py lives in the project root, so __file__ gives us the root directly.
project_dir = os.path.dirname(os.path.abspath(__file__))

from src.loader import load_config, load_rules, load_tabellen
from src.overview import run_overview
from src.utils import get_run_output_dir


def main():
    # Timestamped output folder -- created once, passed to all modules
    run_dir = get_run_output_dir(project_dir)

    config   = load_config(project_dir)
    rules    = load_rules(project_dir)
    tabellen = load_tabellen(config, project_dir)

    print("=" * 60)
    print(f"Projekt: {config['projekt']['git_repository']}")
    print("=" * 60)

    print(f"\nAutor:   {config['projekt']['autor']}")
    print(f"Version: {config['projekt']['version']}")
    print(f"Datum:   {config['projekt']['datum']}")
    print(f"Output:  {run_dir}")

    # Aufgabe 1: Datenueberblick
    print("\n" + "=" * 60)
    print("Aufgabe 1: Datenueberblick")
    print("=" * 60)
    run_overview(tabellen, config, run_dir)
    
    # run_1nf_check(tabellen, rules, run_dir)

    # Aufgabe 2: KPI-Berechnung (TODO)
    # from kpi import run_kpi
    # run_kpi(tabellen, config, rules, run_dir)

    # Aufgabe 3: Dashboard (TODO)
    # from dashboard import run_dashboard
    # run_dashboard(tabellen, config, run_dir)

    print("\nFertig.")


if __name__ == "__main__":
    main()
#%%