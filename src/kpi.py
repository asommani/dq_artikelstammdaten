"""
kpi.py -- Aufgabe 2: KPI-Berechnung Datenqualitaet.

KPIs:
    - Vollstaendigkeit  (Pflichtfelder, konfiguriert in rules.yaml)
    - Eindeutigkeit     (TODO)
    - Konsistenz        (TODO)
"""
import os
import pandas as pd
import numpy as np

from .utils import fehlend_pro_spalte, get_output_dir

try:
    from IPython.display import display
    from IPython import get_ipython
    IN_NOTEBOOK = get_ipython() is not None and get_ipython().__class__.__name__ == "ZMQInteractiveShell"
except ImportError:
    IN_NOTEBOOK = False

try:
    import dataframe_image as dfi
except ImportError:
    dfi = None
    
# ── Vollstaendigkeit ────────────────────────────────────────

def check_vollstaendigkeit(df: pd.DataFrame, pflichtfelder: list[str]) -> pd.DataFrame:
    n = len(df)
    missing = fehlend_pro_spalte(df)[pflichtfelder]

    per_field = pd.DataFrame({
        "feld":             pflichtfelder,
        "fehlend":          missing.values,
        "vollstaendigkeit": (1 - missing / n).values,
    })

    overall = pd.DataFrame([{
        "feld":             "_gesamt",
        "fehlend":          missing.sum(),
        "vollstaendigkeit": 1 - missing.sum() / (n * len(pflichtfelder)),
    }])

    return pd.concat([per_field, overall], ignore_index=True)

def _style_vollstaendigkeit(df_result: pd.DataFrame, table_name: str):
    return (
        df_result.style
        .hide(axis="index")
        .set_caption(f"Vollständigkeit – {table_name}")
        .format({"vollstaendigkeit": "{:.1%}"})
        # .map(
        #     lambda v: "color: red;" if isinstance(v, float) and v < 1.0 else "",
        #     subset=["vollstaendigkeit"]
        # )
    )

def run_vollstaendigkeit(tabellen: dict, rules: dict, config: dict, run_dir: str) -> dict:
    output_dir = get_output_dir(run_dir, "kpis")
    results    = {}
    dpi        = config["export"]["dpi"]

    for tabelle, felder in rules["pflichtfelder"].items():
        result = check_vollstaendigkeit(tabellen[tabelle], felder)
        results[tabelle] = result

        # CSV
        csv_path = os.path.join(output_dir, f"{tabelle}_vollstaendigkeit.csv")
        result.to_csv(csv_path, index=False)
        print(f"  Gespeichert: {os.path.basename(csv_path)}")

        # PNG
        styled  = _style_vollstaendigkeit(result, config["tabellen"][tabelle])
        if config.get("export", {}).get("save_png", False) and dfi is not None:
            png_path = os.path.join(output_dir, f"{tabelle}_vollstaendigkeit.png")
            dfi.export(styled, png_path, table_conversion="matplotlib", dpi=dpi)
            print(f"  Gespeichert: {os.path.basename(png_path)}")

        if IN_NOTEBOOK:
            display(_style_vollstaendigkeit(result, config["tabellen"][tabelle]))

    return results

# ── Eindeutigkeit ────────────────────────────────────────────

def check_eindeutigkeit(df: pd.DataFrame, eindeutigkeit_felder: list[str]) -> pd.DataFrame:
    n = len(df)
    rows = []
    for feld in eindeutigkeit_felder:
        nulls     = int(fehlend_pro_spalte(df)[feld])
        col_clean = df[feld].replace(r"^\s*$", pd.NA, regex=True).dropna()
        eindeutig = col_clean.nunique()
        duplikate = int(col_clean.duplicated().sum())
        rows.append({
            "feld":           feld,
            "gesamt":         n,
            "fehlend":        nulls,
            "eindeutig":      eindeutig,
            "duplikate":      duplikate,
            "eindeutig_rate": eindeutig / n,
        })
    return pd.DataFrame(rows)


def _style_eindeutigkeit(df_result: pd.DataFrame, table_name: str):
    return (
        df_result.style
        .hide(axis="index")
        .set_caption(f"Eindeutigkeit – {table_name}")
        .format({"eindeutig_rate": "{:.1%}"})
    )


def run_eindeutigkeit(tabellen: dict, rules: dict, config: dict, run_dir: str) -> dict:
    output_dir = get_output_dir(run_dir, "kpis")
    dpi        = config["export"]["dpi"]
    results    = {}

    for tabelle, felder in rules["eindeutigkeit_felder"].items():
        result = check_eindeutigkeit(tabellen[tabelle], felder)
        results[tabelle] = result

        # CSV
        csv_path = os.path.join(output_dir, f"{tabelle}_eindeutigkeit.csv")
        result.to_csv(csv_path, index=False)
        print(f"  Gespeichert: {os.path.basename(csv_path)}")

        # PNG
        styled   = _style_eindeutigkeit(result, config["tabellen"][tabelle])
        if config.get("export", {}).get("save_png", False) and dfi is not None:
            png_path = os.path.join(output_dir, f"{tabelle}_eindeutigkeit.png")
            dfi.export(styled, png_path, table_conversion="matplotlib", dpi=dpi)
            print(f"  Gespeichert: {os.path.basename(png_path)}")

        if IN_NOTEBOOK:
            display(styled)

    return results

# ── Konsistenz: Masse ─────────────────────────────────────────

def check_konsistenz_masse(
    df_grund:        pd.DataFrame,
    df_werk:         pd.DataFrame,
    vergleichspaare: list[dict],
    join_key:        list[str],
    abweichung_max:  float,
) -> pd.DataFrame:

    # deduplicate Werksdaten: exact duplicates first, then composite key
    df_werk_clean = df_werk.drop_duplicates().drop_duplicates(subset=join_key)

    # extract column name lists from config
    cols_grund = [p["grund"] for p in vergleichspaare]
    cols_werk  = [p["werk"]  for p in vergleichspaare]

    # join keys per table
    join_key_grund = [k for k in join_key if k in df_grund.columns]
    join_key_werk  = [k for k in join_key if k in df_werk_clean.columns]

    # inner join
    merged = df_grund[join_key_grund + cols_grund].merge(
        df_werk_clean[join_key_werk + cols_werk],
        on=join_key_grund,
        how="inner",
    )
    n_gesamt = len(merged)

    all_dim_cols = cols_grund + cols_werk

    # null check is sufficient here: dimension columns are float64,
    # blank/whitespace strings cannot occur
    mask_null    = merged[all_dim_cols].isnull().any(axis=1)
    comparable   = merged[~mask_null]
    n_comparable = len(comparable)

    # vectorized max relative deviation across all dimension pairs
    grund_vals = comparable[cols_grund].values
    werk_vals  = comparable[cols_werk].values

    max_dev = (
    np.abs(grund_vals - werk_vals)
    / np.where(grund_vals == 0, np.nan, grund_vals) # avoid division by zero; pairs with grund=0 are excluded from comparison
    ).max(axis=1)

    n_inkonsistent = int((max_dev > abweichung_max).sum())
    n_konsistent   = n_comparable - n_inkonsistent

    return pd.DataFrame([{
        "paare_gesamt":      n_gesamt,
        "ausgeschlossen":    int(mask_null.sum()),
        "vergleichbar":      n_comparable,
        "konsistent":        n_konsistent,
        "konsistent_rate":   n_konsistent   / n_comparable if n_comparable > 0 else None,
        "inkonsistent":      n_inkonsistent,
        "inkonsistent_rate": n_inkonsistent / n_comparable if n_comparable > 0 else None,
        "_sanity_check":     int(mask_null.sum()) + n_konsistent + n_inkonsistent == n_gesamt,
    }])


def _style_konsistenz_masse(df_result: pd.DataFrame) -> pd.Styler:
    return (
        df_result.style
        .hide(axis="index")
        .set_caption("Konsistenz – Maße Grunddaten vs. Werksdaten")
        .format({
            "konsistent_rate":   "{:.1%}",
            "inkonsistent_rate": "{:.1%}",
        })
    )


def run_konsistenz_masse(tabellen: dict, rules: dict, config: dict, run_dir: str) -> pd.DataFrame:
    output_dir = get_output_dir(run_dir, "kpis")
    dpi        = config["export"]["dpi"]
    cfg        = rules["konsistenz_masse"]

    result = check_konsistenz_masse(
        df_grund        = tabellen[cfg["tabellen"]["grund"]],
        df_werk         = tabellen[cfg["tabellen"]["werk"]],
        vergleichspaare = cfg["vergleichspaare"],
        join_key        = cfg["join_key"],
        abweichung_max  = rules["schwellenwerte"]["konsistenz_abweichung_max"],
    )

    # CSV
    csv_path = os.path.join(output_dir, "konsistenz_masse.csv")
    result.to_csv(csv_path, index=False)
    print(f"  Gespeichert: {os.path.basename(csv_path)}")

    # PNG
    styled   = _style_konsistenz_masse(result)
    if config.get("export", {}).get("save_png", False) and dfi is not None:
        png_path = os.path.join(output_dir, "konsistenz_masse.png")
        dfi.export(styled, png_path, table_conversion="matplotlib", dpi=dpi)
        print(f"  Gespeichert: {os.path.basename(png_path)}")

    if IN_NOTEBOOK:
        display(styled)

    return result

# ── Konsistenz: Einheit Masse ─────────────────────────────────

def check_konsistenz_einheit_masse(
    tabellen: dict,
    checks:   list[dict],
    rules:    dict,
) -> pd.DataFrame:
    rows = []
    for check in checks:
        df      = tabellen[check["tabelle"]]
        spalte  = check["spalte"]
        gueltig = rules
        for key in check["gueltige_werte"].split("."):
            gueltig = gueltig[key]

        col          = df[spalte].replace(r"^\s*$", pd.NA, regex=True)
        n_gesamt     = len(col)
        n_fehlend    = int(col.isnull().sum())
        col_present  = col.dropna()
        mask_invalid = ~col_present.isin(gueltig)
        n_invalid    = int(mask_invalid.sum())
        n_valid      = n_gesamt - n_fehlend - n_invalid

        rows.append({
            "tabelle":          check["tabelle"],
            "spalte":           spalte,
            "gueltig":          ", ".join(gueltig),
            "gesamt":           n_gesamt,
            "fehlend":          n_fehlend,
            "valid":            n_valid,
            "valid_rate":       n_valid   / n_gesamt if n_gesamt > 0 else None,
            "invalid":          n_invalid,
            "invalid_rate":     n_invalid / n_gesamt if n_gesamt > 0 else None,
            "vorhandene_werte": col_present.value_counts().to_dict(),
            "invalid_werte":    col_present[mask_invalid].unique().tolist(),
            "einheitlich":      n_invalid == 0 and n_fehlend == 0,
        })
    return pd.DataFrame(rows)

def _style_konsistenz_einheit_masse(df_result: pd.DataFrame) -> pd.Styler:
    return (
        df_result.style
        .hide(axis="index")
        .set_caption("Konsistenz – Einheitlichkeit der Maßeinheiten")
        .format({"invalid_rate": "{:.1%}", "valid_rate": "{:.1%}"})
    )


def run_konsistenz_einheit_masse(tabellen: dict, rules: dict, config: dict, run_dir: str) -> pd.DataFrame:
    output_dir = get_output_dir(run_dir, "kpis")
    dpi        = config["export"]["dpi"]

    result = check_konsistenz_einheit_masse(
        tabellen = tabellen,
        checks   = rules["konsistenz_einheit_masse"],
        rules    = rules,
    )

    # CSV
    csv_path = os.path.join(output_dir, "konsistenz_einheit_masse.csv")
    result.to_csv(csv_path, index=False)
    print(f"  Gespeichert: {os.path.basename(csv_path)}")

    # PNG
    styled   = _style_konsistenz_einheit_masse(result)
    if config.get("export", {}).get("save_png", False) and dfi is not None:
        png_path = os.path.join(output_dir, "konsistenz_einheit_masse.png")
        dfi.export(styled, png_path, table_conversion="matplotlib", dpi=dpi)
        print(f"  Gespeichert: {os.path.basename(png_path)}")

    if IN_NOTEBOOK:
        display(styled)

    return result


#%%
##--------- Aufgabe 3 extra analysis ----------------
# ── Plausibilitaet: Masse ─────────────────────────────────────

def check_plausibilitaet_masse(
    tabellen: dict,
    checks:   list[dict],
) -> pd.DataFrame:
    rows = []
    for check in checks:
        df      = tabellen[check["tabelle"]]
        spalten = check["spalten"]

        mask_null        = df[spalten].isnull().any(axis=1)
        mask_implausibel = (~mask_null) & (df[spalten] <= 0).any(axis=1)

        n_gesamt      = len(df)
        n_null        = int(mask_null.sum())
        n_implausibel = int(mask_implausibel.sum())
        n_plausibel   = n_gesamt - n_null - n_implausibel

        rows.append({
            "tabelle":        check["tabelle"],
            "spalten":        ", ".join(spalten),
            "gesamt":         n_gesamt,
            "fehlend":        n_null,
            "implausibel":    n_implausibel,
            "implausibel_rate": n_implausibel / n_gesamt if n_gesamt > 0 else None,
            "plausibel":      n_plausibel,
            "plausibel_rate": n_plausibel / n_gesamt if n_gesamt > 0 else None,
        })
    return pd.DataFrame(rows)


def _style_plausibilitaet_masse(df_result: pd.DataFrame) -> pd.Styler:
    return (
        df_result.style
        .hide(axis="index")
        .set_caption("Plausibilität – Maße (Nullwerte & Negativwerte)")
        .format({"plausibel_rate": "{:.1%}",
                 "implausibel_rate": "{:.1%}",
                 })
    )


def run_plausibilitaet_masse(tabellen: dict, rules: dict, config: dict, run_dir: str) -> pd.DataFrame:
    output_dir = get_output_dir(run_dir, "kpis")
    dpi        = config["export"]["dpi"]

    result = check_plausibilitaet_masse(
        tabellen = tabellen,
        checks   = rules["plausibilitaet_masse"],
    )

    # CSV
    csv_path = os.path.join(output_dir, "plausibilitaet_masse.csv")
    result.to_csv(csv_path, index=False)
    print(f"  Gespeichert: {os.path.basename(csv_path)}")

    # PNG
    styled   = _style_plausibilitaet_masse(result)
    if config.get("export", {}).get("save_png", False) and dfi is not None:
        png_path = os.path.join(output_dir, "plausibilitaet_masse.png")
        dfi.export(styled, png_path, table_conversion="matplotlib", dpi=dpi)
        print(f"  Gespeichert: {os.path.basename(png_path)}")

    if IN_NOTEBOOK:
        display(styled)

    return result

# ── GTIN / EAN-13 Formatpruefung ─────────────────────────────

def check_gtin_format(
    tabellen:   dict,
    gtin_check: dict,
) -> pd.DataFrame:
    df     = tabellen[gtin_check["tabelle"]]
    spalte = gtin_check["spalte"]
    laenge = gtin_check["laenge"]

    col       = df[spalte].dropna()
    n_gesamt  = len(df)
    n_fehlend = int(df[spalte].isnull().sum())

    gtin_str     = col.astype(int).astype(str)
    mask_invalid = gtin_str.str.len() != laenge
    n_invalid    = int(mask_invalid.sum())
    n_valid      = n_gesamt - n_fehlend - n_invalid

    return pd.DataFrame([{
        "tabelle":      gtin_check["tabelle"],
        "spalte":       spalte,
        "gesamt":       n_gesamt,
        "fehlend":      n_fehlend,
        "valid":        n_valid,
        "valid_rate":   n_valid   / n_gesamt if n_gesamt > 0 else None,
        "invalid":      n_invalid,
        "invalid_rate": n_invalid / n_gesamt if n_gesamt > 0 else None,
    }])

def _style_gtin_format(df_result: pd.DataFrame) -> pd.Styler:
    return (
        df_result.style
        .hide(axis="index")
        .set_caption("GTIN – EAN-13 Formatprüfung")
        .format({
            "valid_rate":   "{:.1%}",
            "invalid_rate": "{:.1%}",
        })
    )


def run_gtin_format(tabellen: dict, rules: dict, config: dict, run_dir: str) -> pd.DataFrame:
    output_dir = get_output_dir(run_dir, "kpis")
    dpi        = config["export"]["dpi"]

    result = check_gtin_format(
        tabellen   = tabellen,
        gtin_check = rules["gtin_check"],
    )

    # CSV
    csv_path = os.path.join(output_dir, "gtin_format.csv")
    result.to_csv(csv_path, index=False)
    print(f"  Gespeichert: {os.path.basename(csv_path)}")

    # PNG
    styled   = _style_gtin_format(result)
    if config.get("export", {}).get("save_png", False) and dfi is not None:
        png_path = os.path.join(output_dir, "gtin_format.png")
        dfi.export(styled, png_path, table_conversion="matplotlib", dpi=dpi)
        print(f"  Gespeichert: {os.path.basename(png_path)}")

    if IN_NOTEBOOK:
        display(styled)

    return result

def run_validitaet_vokabular(tabellen: dict, rules: dict, config: dict, run_dir: str) -> pd.DataFrame:
    output_dir = get_output_dir(run_dir, "kpis")
    dpi        = config["export"]["dpi"]

    result = check_konsistenz_einheit_masse(
        tabellen = tabellen,
        checks   = rules["validitaet_vokabular"],
        rules    = rules,
    ).drop(columns=["einheitlich"])

    # CSV
    csv_path = os.path.join(output_dir, "validitaet_vokabular.csv")
    result.to_csv(csv_path, index=False)
    print(f"  Gespeichert: {os.path.basename(csv_path)}")

    # PNG
    styled   = (
        result.style
        .hide(axis="index")
        .set_caption("Validität – Kontrollierte Vokabulare")
        .format({"valid_rate": "{:.1%}", "invalid_rate": "{:.1%}"})
    )
    if config.get("export", {}).get("save_png", False) and dfi is not None:
        png_path = os.path.join(output_dir, "validitaet_vokabular.png")
        dfi.export(styled, png_path, table_conversion="matplotlib", dpi=dpi)
        print(f"  Gespeichert: {os.path.basename(png_path)}")

    if IN_NOTEBOOK:
        display(styled)

    return result