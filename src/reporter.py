"""
reporter.py -- Aufgabe 3: Auswertung der Datenqualitaetsprobleme.

Checks pulling in supporting tables (Preise, Kategorisierung, Werksdaten):
    - check_preisvalidierung
    - check_referenzintegritaet
    - check_werksdaten_konflikte
"""

import os
from networkx import config
import pandas as pd
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


# ── Preisvalidierung ──────────────────────────────────────────

def check_preisvalidierung(
    df:              pd.DataFrame,
    uvp_spalte:      str,
    waehrung_spalte: str,
    sentinel_werte:  list,
    preis_min:       float,
    preis_max:       float,
    gueltige_waehrung: list,
) -> pd.DataFrame:
    n_gesamt    = len(df)

    mask_sentinel  = df[uvp_spalte].isin(sentinel_werte)
    mask_range     = (~mask_sentinel) & (
        (df[uvp_spalte] < preis_min) | (df[uvp_spalte] > preis_max)
    )
    mask_waehrung  = ~df[waehrung_spalte].isin(gueltige_waehrung)
    mask_invalid   = mask_sentinel | mask_range | mask_waehrung
    n_invalid      = int(mask_invalid.sum())
    n_valid        = n_gesamt - n_invalid

    return pd.DataFrame([{
        "gesamt":              n_gesamt,
        "sentinel":            int(mask_sentinel.sum()),
        "ausserhalb_range":    int(mask_range.sum()),
        "ungueltige_waehrung":       int(mask_waehrung.sum()),
        "ungueltige_waehrung_werte": df.loc[mask_waehrung, waehrung_spalte].unique().tolist(),
        "invalid_gesamt":      n_invalid,
        "invalid_rate":        n_invalid / n_gesamt if n_gesamt > 0 else None,
        "valid":               n_valid,
        "valid_rate":          n_valid   / n_gesamt if n_gesamt > 0 else None,
    }])


def _style_preisvalidierung(df_result: pd.DataFrame) -> pd.Styler:
    return (
        df_result.style
        .hide(axis="index")
        .set_caption("Preisvalidierung – Sentinel, Wertebereich, Währung")
        .format({"valid_rate": "{:.1%}",
                 "invalid_rate": "{:.1%}"
                 })
    )


def run_preisvalidierung(tabellen: dict, rules: dict, config: dict, run_dir: str) -> pd.DataFrame:
    output_dir = get_output_dir(run_dir, "reporter")
    dpi        = config["export"]["dpi"]
    cfg        = rules["preisvalidierung"]

    # resolve gueltige_waehrung via dotted path
    gueltige_waehrung = rules
    for key in cfg["gueltige_werte"].split("."):
        gueltige_waehrung = gueltige_waehrung[key]

    result = check_preisvalidierung(
        df               = tabellen[cfg["tabelle"]],
        uvp_spalte       = cfg["uvp_spalte"],
        waehrung_spalte  = cfg["waehrung_spalte"],
        sentinel_werte   = cfg["sentinel_werte"],
        preis_min        = rules["schwellenwerte"]["preis_min"],
        preis_max        = rules["schwellenwerte"]["preis_max"],
        gueltige_waehrung = gueltige_waehrung,
    )

    # CSV
    csv_path = os.path.join(output_dir, "preisvalidierung.csv")
    result.to_csv(csv_path, index=False)
    print(f"  Gespeichert: {os.path.basename(csv_path)}")

    # PNG
    styled   = _style_preisvalidierung(result)
    if config.get("export", {}).get("save_png", False) and dfi is not None:
        png_path = os.path.join(output_dir, "preisvalidierung.png")
        dfi.export(styled, png_path, table_conversion="matplotlib", dpi=dpi)
        print(f"  Gespeichert: {os.path.basename(png_path)}")

    if IN_NOTEBOOK:
        display(styled)

    return result


# ── Referenzintegritaet ───────────────────────────────────────
# for every row in Kategorisierung, does the Artikelnummer exist in Grunddaten?
def check_referenzintegritaet(
    df:               pd.DataFrame,
    df_referenz:      pd.DataFrame,
    spalte:           str,
    referenz_spalte:  str,
) -> pd.DataFrame:
    valid_ids          = set(df_referenz[referenz_spalte].dropna())
    unique_ids         = df[spalte].dropna().unique()
    n_unique           = len(unique_ids)
    mask_orphan        = ~pd.Series(unique_ids).isin(valid_ids)
    n_orphan           = int(mask_orphan.sum())
    n_valid            = n_unique - n_orphan

    return pd.DataFrame([{
        "eindeutige_artikel": n_unique,
        "referenziert":       n_valid,
        "verwaist":           n_orphan,
        "verwaist_rate":      n_orphan / n_unique if n_unique > 0 else None,
    }])

def _style_referenzintegritaet(df_result: pd.DataFrame, caption: str) -> pd.Styler:
    return (
        df_result.style
        .hide(axis="index")
        .set_caption(caption)
        .format({
            "verwaist_rate":   "{:.1%}",
        })
    )

def run_referenzintegritaet(tabellen: dict, rules: dict, config: dict, run_dir: str) -> dict:
    output_dir = get_output_dir(run_dir, "reporter")
    dpi        = config["export"]["dpi"]
    results    = {}

    for check in rules["referenzintegritaet"]:
        result = check_referenzintegritaet(
            df              = tabellen[check["tabelle"]],
            df_referenz     = tabellen[check["referenz_tabelle"]],
            spalte          = check["spalte"],
            referenz_spalte = check["referenz_spalte"],
        )
        results[check["tabelle"]] = result

        name     = f"{check['tabelle']}_referenzintegritaet"
        caption  = f"Referenzintegrität – {config['tabellen'][check['tabelle']]}"

        # CSV
        csv_path = os.path.join(output_dir, f"{name}.csv")
        result.to_csv(csv_path, index=False)
        print(f"  Gespeichert: {os.path.basename(csv_path)}")

        # PNG
        styled   = _style_referenzintegritaet(result, caption)
        if config.get("export", {}).get("save_png", False) and dfi is not None:
            png_path = os.path.join(output_dir, f"{name}.png")
            dfi.export(styled, png_path, table_conversion="matplotlib", dpi=dpi)
            print(f"  Gespeichert: {os.path.basename(png_path)}")

        if IN_NOTEBOOK:
            display(styled)

    return results


# ── Werksdaten Konflikte ──────────────────────────────────────

def check_werksdaten_konflikte(
    df:       pd.DataFrame,
    join_key: list[str],
) -> pd.DataFrame:
    n_roh          = len(df)
    n_exakt_dups   = int(df.duplicated().sum())
    df_dedup       = df.drop_duplicates()
    n_konflikte    = int(df_dedup.duplicated(subset=join_key).sum())
    df_clean       = df_dedup.drop_duplicates(subset=join_key)
    n_clean        = len(df_clean)

    return pd.DataFrame([{
        "zeilen_roh":          n_roh,
        "exakte_duplikate":    n_exakt_dups,
        "konflikte":           n_konflikte,
        "zeilen_nach_bereinigung": n_clean,
    }])


def _style_werksdaten_konflikte(df_result: pd.DataFrame) -> pd.Styler:
    return (
        df_result.style
        .hide(axis="index")
        .set_caption("Werksdaten – Duplikate & Konflikte")
    )


def run_werksdaten_konflikte(tabellen: dict, rules: dict, config: dict, run_dir: str) -> pd.DataFrame:
    output_dir = get_output_dir(run_dir, "reporter")
    dpi        = config["export"]["dpi"]
    cfg        = rules["konsistenz_masse"]
    join_key   = cfg["join_key"]
    df         = tabellen[cfg["tabellen"]["werk"]]

    # recompute conflicts for export
    df_dedup    = df.drop_duplicates()
    konflikte   = df_dedup[df_dedup.duplicated(subset=join_key, keep=False)]

    result = check_werksdaten_konflikte(
        df       = df,
        join_key = join_key,
    )

    # CSV summary
    csv_path = os.path.join(output_dir, "werksdaten_konflikte_summary.csv")
    result.to_csv(csv_path, index=False)
    print(f"  Gespeichert: {os.path.basename(csv_path)}")

    # CSV conflicts detail
    konflikte_path = os.path.join(output_dir, "werksdaten_konflikte_detail.csv")
    konflikte.to_csv(konflikte_path, index=False)
    print(f"  Gespeichert: {os.path.basename(konflikte_path)}")

   
    styled   = _style_werksdaten_konflikte(result)
    # PNG summary
    if config.get("export", {}).get("save_png", False) and dfi is not None:
        png_path = os.path.join(output_dir, "werksdaten_konflikte_summary.png")
        dfi.export(styled, png_path, table_conversion="matplotlib", dpi=dpi)
        print(f"  Gespeichert: {os.path.basename(png_path)}")
    styled_detail = konflikte.style.hide(axis="index").set_caption("Werksdaten – Konfliktpaare (Detail)")
    
    if config.get("export", {}).get("save_png", False) and dfi is not None:
        png_detail_path = os.path.join(output_dir, "werksdaten_konflikte_detail.png")
        dfi.export(styled_detail, png_detail_path, table_conversion="matplotlib", dpi=dpi)
        print(f"  Gespeichert: {os.path.basename(png_detail_path)}")

    if IN_NOTEBOOK:
        display(styled)
        if IN_NOTEBOOK and len(konflikte) > 0:
            display(konflikte.style.set_caption("Werksdaten – Konfliktpaare (Detail)"))

    return result

# ─--- check articles without werksdaten ──────────────────────────────────────



def check_artikel_ohne_werksdaten(
    df_grund: pd.DataFrame,
    df_werk:  pd.DataFrame,
    join_key: list[str],
) -> pd.DataFrame:
    join_key_grund = [k for k in join_key if k in df_grund.columns]
    
    ids_grund  = set(df_grund[join_key_grund[0]])
    ids_werk   = set(df_werk[join_key_grund[0]])
    ohne_werk  = ids_grund - ids_werk
    
    return pd.DataFrame([{
        "artikel_gesamt":      len(ids_grund),
        "mit_werksdaten":      len(ids_grund & ids_werk),
        "ohne_werksdaten":     len(ohne_werk),
        "ohne_werksdaten_rate": len(ohne_werk) / len(ids_grund) if ids_grund else None,
        "artikelnummern":      sorted(ohne_werk),
    }])


def _style_artikel_ohne_werksdaten(df_result: pd.DataFrame) -> pd.Styler:
    return (
        df_result.style
        .hide(axis="index")
        .set_caption("Artikel ohne Werksdateneintrag")
        .format({"ohne_werksdaten_rate": "{:.1%}"})
    )


def run_artikel_ohne_werksdaten(tabellen: dict, rules: dict, config: dict, run_dir: str) -> pd.DataFrame:
    output_dir = get_output_dir(run_dir, "reporter")
    dpi        = config["export"]["dpi"]
    cfg        = rules["konsistenz_masse"]

    result = check_artikel_ohne_werksdaten(
        df_grund = tabellen[cfg["tabellen"]["grund"]],
        df_werk  = tabellen[cfg["tabellen"]["werk"]],
        join_key = cfg["join_key"],
    )

    # CSV
    csv_path = os.path.join(output_dir, "artikel_ohne_werksdaten.csv")
    result.to_csv(csv_path, index=False)
    print(f"  Gespeichert: {os.path.basename(csv_path)}")

    # PNG
    styled   = _style_artikel_ohne_werksdaten(result)
    if config.get("export", {}).get("save_png", False) and dfi is not None:
        png_path = os.path.join(output_dir, "artikel_ohne_werksdaten.png")
        dfi.export(styled, png_path, table_conversion="matplotlib", dpi=dpi)
        print(f"  Gespeichert: {os.path.basename(png_path)}")

    if IN_NOTEBOOK:
        display(styled)

    return result

