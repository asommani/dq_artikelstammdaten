#%%
import os
from IPython.display import display
import pandas as pd
import matplotlib.pyplot as plt
import yaml
from matplotlib.backends.backend_pdf import PdfPages
import dataframe_image as dfi



#%% ── Pfade definieren ────────────────────────────────────

project_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(project_dir, 'config', 'config.yaml')
raw_data_dir = os.path.join(project_dir, 'data', 'raw')
output_dir = os.path.join(project_dir, 'output')

#%% ── Config laden ────────────────────────────────────
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)
#%% ── Excel-Datei laden ────────────────────────────────────
artikelstammdaten = pd.ExcelFile(os.path.join(raw_data_dir, config['datei']['filename']))

# Überprüfen, ob die Schlüssel in den Konfigurationstabellen mit den Blattnamen in der Excel-Datei übereinstimmen
assert set(config['tabellen'].values()) == set(artikelstammdaten.sheet_names), "Die Tabellennamen in der config.yaml stimmen nicht mit den Blattnamen in der Excel-Datei überein."

#%% ── Tabellenblätter laden und erste infos ────────────────────────────────────
tabellen = {}
for var_name, sheet_name in config["tabellen"].items():
    tabellen[var_name] = artikelstammdaten.parse(sheet_name)
    print(f"--- {sheet_name} ---")
    print(f"Zeilen: {len(tabellen[var_name])}, Spalten: {len(tabellen[var_name].columns)}")
    print(f"Spaltennamen: {list(tabellen[var_name].columns)}")
    #print(tabellen[var_name].head(3))

#%%──── Aufgabe 1: Datenüberblick ────────────────────────────────────────────────────────────────────────────
os.makedirs(os.path.join(output_dir, "datenüberblick"), exist_ok=True)

def highlight_missing(val):
    return "color: red;" if val > 0 else ""
#%%
for var_name, df in tabellen.items():
    table_name = config["tabellen"][var_name]
    total_zellen = len(df) * len(df.columns)
    uebersicht = pd.DataFrame({
        "Merkmal": [
            "Zeilen",
            "Spalten", 
            #"Eindeutige Artikelnummer",
            "NaN",
            "Leere/WS",
            ### this is more duplicate rows, not duplicate values in a specific column, so we use df.duplicated() without subset
            ### Better to show duplicate rows or duplicate values in a specific column? I think duplicate rows is more informative for data quality, so I will use that.
            "Duplikate Zeilen"
        ],
        "Wert": [
            len(df),
            len(df.columns),
            #df["Artikelnummer"].nunique() if "Artikelnummer" in df.columns else "—",
            df.isna().sum().sum(),
            sum((df[col].str.strip() == "").sum() for col in df.select_dtypes(include="object").columns),
            df.duplicated().sum()
        ],
        "Prozent": [
            "—",
            "—",
            #f"{df['Artikelnummer'].nunique() / len(df) * 100:.1f}%" if "Artikelnummer" in df.columns else "—",
            f"{df.isna().sum().sum() / total_zellen * 100:.1f}%",
            f"{sum((df[col].str.strip() == '').sum() for col in df.select_dtypes(include='object').columns) / total_zellen * 100:.1f}%",
            f"{df.duplicated().sum() / len(df) * 100:.1f}%"

        ]  
    })

    uebersicht_styled = uebersicht.style.set_caption(table_name)
    # show the tabl ein the interactive environment
    display(uebersicht_styled)

    dfi.export(
        uebersicht_styled,
        os.path.join(output_dir, "datenüberblick", f"{table_name}_uebersicht.png"),
        table_conversion="matplotlib",
        dpi=config['export']['bilder']['dpi']*0.5
    )
#%%
for var_name, df in tabellen.items():
    table_name = config["tabellen"][var_name]

    # ── Fehlende Werte berechnen (NaN + leer + whitespace) ───
    nan_pro_spalte  = df.isna().sum()
    leer_pro_spalte = pd.Series(0, index=df.columns)
    for col in df.columns:
        if df[col].dtype == "object" or hasattr(df[col], "str"):
            try:
                leer_pro_spalte[col] = (df[col].str.strip() == "").sum()
            except AttributeError:
                pass  # Spalte hat keine str-Methoden, überspringen
    gesamt_pro_spalte = nan_pro_spalte + leer_pro_spalte

    # # Diagnostik
    # if leer_pro_spalte.sum() == 0:
    #     print(f"  ✓ {var_name}: Keine leeren/whitespace Einträge gefunden")
    # else:
    #     print(f"  ⚠ {var_name}: {leer_pro_spalte.sum()} leere/whitespace Einträge gefunden")

    # ── DataFrame aufbauen ────────────────────────────────────
    spalten_detail = pd.DataFrame({
        "Spalte":           df.columns,
        "Datentyp":         df.dtypes.values,
        "Gesamt fehlend":   gesamt_pro_spalte.values,
        "% Fehlend":        [f"{x:.1f}%" for x in (gesamt_pro_spalte / len(df) * 100).values],
        "Eindeutige Werte": df.nunique().values,
        "% Eindeutig":      [f"{x:.1f}%" for x in (df.nunique() / len(df) * 100).values],
    })

    # ── Styling ───────────────────────────────────────────────
    gesamt_fehlend_gesamt = gesamt_pro_spalte.sum()
    gesamt_fehlend_pct    = gesamt_fehlend_gesamt / (len(df) * len(df.columns)) * 100

    spalten_detail_styled = (
        spalten_detail.style
        .hide(axis="index")
        .set_caption(
            f"{table_name} — "
            f"Zeilen: {len(df)}, "
            f"Spalten: {len(df.columns)}, "
            f"Fehlend: {gesamt_fehlend_pct:.1f}%, "
            f"Duplizierte Zeilen: {int(df.duplicated().sum())}"
        )
        .map(lambda v: "color: red; "
        #"font-weight: bold;"
          if isinstance(v, (int, float)) and v > 0 else "",
             subset=["Gesamt fehlend"])
    )

    display(spalten_detail_styled)

    dfi.export(
        spalten_detail_styled,
        os.path.join(output_dir, "datenüberblick", f"{table_name}_spalten_detail.png"),
        table_conversion="matplotlib",
        dpi=config["export"]["bilder"]["dpi"]
    )
#%%
for var_name, df in tabellen.items():
    table_name = config["tabellen"][var_name]
    df_head_styled = df.head(10).style.set_caption(f"{table_name} — erste Zeilen")
    display(df_head_styled)

    dfi.export(
        df_head_styled,
        os.path.join(output_dir, "datenüberblick", f"{table_name}_head.png"),
        table_conversion="matplotlib",
        dpi=config["export"]["bilder"]["dpi"]
    )
# %%
