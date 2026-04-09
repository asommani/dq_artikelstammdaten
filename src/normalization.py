"""
normalization.py -- Aufgabe 1: Normalformanalyse.

Automated check:
    - run_1nf_check(): flags potential 1NF violations (non-atomic values)
      based on delimiter heuristic defined in rules.yaml.

Note:
    2NF and 3NF analysis requires domain knowledge and cannot be fully
    automated. Findings are documented in docs/annahmen.md and the
    accompanying presentation.
"""

import os
import re
import pandas as pd
from .utils import get_output_dir

try:
    from IPython.display import display
    IN_NOTEBOOK = True
except ImportError:
    IN_NOTEBOOK = False


# ── Computation ───────────────────────────────────────────────

def flag_check_1nf(df: pd.DataFrame, delimiters: list[str]) -> pd.DataFrame:
    """
    Flags cells containing delimiter characters as *candidates*
    for non-atomicity. Requires human judgment to confirm whether
    a flagged value is a genuine violation or a legitimate compound name.

    Args:
        df:         DataFrame to check.
        delimiters: List of delimiter strings from rules.yaml.

    Returns:
        DataFrame with columns: column, row_index, value.
        Empty DataFrame if no candidates found.
    """
    violations = []
    pattern = '|'.join(re.escape(d) for d in delimiters)

    for col in df.select_dtypes(include='object').columns:
        mask = df[col].str.contains(pattern, na=False)
        for idx in df[mask].index:
            violations.append({
                'column':    col,
                'row_index': idx,
                'value':     df.at[idx, col],
            })

    return pd.DataFrame(violations)


# ── Hauptfunktion ─────────────────────────────────────────────

def run_1nf_check(tabellen: dict, rules: dict, run_dir: str) -> None:
    """
    Runs 1NF atomicity check for all tables and saves flagged
    candidates to CSV in the normalisierungsanalyse/ subfolder.

    Flagged values are candidates only -- human judgment is required
    to confirm whether a value is a genuine violation or a legitimate
    compound label (e.g. product names, addresses).

    Args:
        tabellen:  Dict var_name -> DataFrame (aus loader.py)
        rules:     Geladene rules.yaml
        run_dir:   Timestamped output folder fuer diesen Run
    """
    output_dir = get_output_dir(run_dir, "normalisierungsanalyse")
    delimiters = rules["atomicity_delimiters"]

    for var_name, df in tabellen.items():
        violations = flag_check_1nf(df, delimiters)
        print(f"\n-- 1NF Check: {var_name} --")

        if violations.empty:
            print("  Keine potenziellen 1NF-Verletzungen gefunden.")
        else:
            print(f"  {len(violations)} Kandidaten geflaggt.")
            if IN_NOTEBOOK:
                display(violations)
            output_path = os.path.join(
                output_dir, f"{var_name}_1nf_violations_flagged.csv"
            )
            violations.to_csv(output_path, index=False)
            print(f"  Gespeichert: {os.path.basename(output_path)}")