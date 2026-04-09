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
from src.utils import get_run_output_dir
from src.overview import run_overview
from src.normalization import run_1nf_check
from src.kpi import run_konsistenz_einheit_masse, run_vollstaendigkeit, run_eindeutigkeit, run_konsistenz_masse


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
    # boolean flag for 1nf yer o not (in config)
    if config.get("normalization", {}).get("check_1nf"):
        print("\n" + "=" * 60)
        print("Aufgabe 1b: 1NF-Atomicity Check")
        print("=" * 60)
        run_1nf_check(tabellen, rules, run_dir)

    # Aufgabe 2: KPI-Berechnung
    print("\n" + "=" * 60)
    print("Aufgabe 2: KPI-Berechnung")
    print("=" * 60)

    vollstaendigkeit_results  = run_vollstaendigkeit(tabellen, rules, config, run_dir)
    eindeutigkeit_results     = run_eindeutigkeit(tabellen, rules, config, run_dir)
    konsistenz_masse_result   = run_konsistenz_masse(tabellen, rules, config, run_dir)
    konsistenz_einheit_masse = run_konsistenz_einheit_masse(tabellen, rules, config, run_dir)


    # Aufgabe 3: Dashboard (TODO)
    # from dashboard import run_dashboard
    # run_dashboard(tabellen, config, run_dir)

    print("\nFertig.")


if __name__ == "__main__":
    main()
#%%