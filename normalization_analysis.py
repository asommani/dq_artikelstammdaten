#%%
import os
import pandas as pd
#this script lives in the project root, so __file__ gives us the root directly.
project_dir = os.path.dirname(os.path.abspath(__file__))

from src.loader import load_config, load_rules, load_tabellen
from src.normalization import run_1nf_check
from src.utils import get_run_output_dir

run_dir = get_run_output_dir(project_dir)
config   = load_config(project_dir)
rules = load_rules(project_dir)
tabellen = load_tabellen(config, project_dir)

print(f"Output:  {run_dir}")
#%% ============= 1NF Check ================
run_1nf_check(tabellen, rules, run_dir)

#%%## single tables analysis for PK and 2NF violations
### ============= PKs and 2NF of kategorisierung.======================

df = tabellen["kategorisierung"].drop_duplicates()
print(f"Original rows: {len(tabellen["kategorisierung"])}")
print(f"Rows after dropping duplicates: {len(df)}")

# show that Artikelnummer alone is not unique
print(f"Zeilen gesamt:         {len(df)}")
print(f"Eindeutige Artikelnr.: {df['Artikelnummer'].nunique()}")
print(df.columns)
#%%
# show that even all columns together don't give a clean key
combos = [
    ["Artikelnummer"],
    ["Artikelnummer", "Kategorie"],
    ["Artikelnummer", "Kategorie", "Unterkategorie"],
    ["Artikelnummer", "Kategorie", "Unterkategorie", "Saison"],
    ["Artikelnummer", "Kategorie", "Unterkategorie", "Saison", "Zielgruppe"],
    ["Artikelnummer", "Kategorie", "Saison"],
    ["Artikelnummer", "Kategorie", "Zielgruppe"],
]

for cols in combos:
    dups = df.duplicated(subset=cols).sum()
    print(f"{cols}: {dups} Duplikate")

# ========== Junction tables for 2NF Kategorisierung checks ==========
# what if I create junction tables:
# Artikel_Kategorie (Artikelnummer, Kategorie, Unterkategorie)
# Artikel_Saison (Artikelnummer, Saison)
# Artikel_Zielgruppe (Artikelnummer, Zielgruppe)

# df = tabellen["kategorisierung"].drop_duplicates()
# artikel_kategorie  = df[["Artikelnummer", "Kategorie", "Unterkategorie"]].drop_duplicates()
# artikel_saison     = df[["Artikelnummer", "Saison"]].drop_duplicates()
# artikel_zielgruppe = df[["Artikelnummer", "Zielgruppe"]].drop_duplicates()
# # verify composite keys are clean
# assert artikel_kategorie.duplicated().sum()  == 0
# assert artikel_saison.duplicated().sum()     == 0
# assert artikel_zielgruppe.duplicated().sum() == 0

# print(f"Artikel_Kategorie:  {len(artikel_kategorie)} Zeilen")
# print(f"Artikel_Saison:     {len(artikel_saison)} Zeilen")
# print(f"Artikel_Zielgruppe: {len(artikel_zielgruppe)} Zeilen")

#%%
# ================ Preise table 2NF ================
df = tabellen["preise"]
# show that Artikelnummer alone is not unique
print(f"Zeilen gesamt:         {len(df)}")
print(f"Eindeutige Artikelnr.: {df['Artikelnummer'].nunique()}")
print()
# check combinations of Artikelnummer with other columns for uniqueness
combos = [
    ["Artikelnummer"],
    ["Artikelnummer", "Währung"],
    ["Artikelnummer", "Gültig_ab"],
    ["Artikelnummer","Währung", "Gültig_ab"]
]
for cols in combos:
    dups = df.duplicated(subset=cols).sum()
    print(f"{cols}: {dups} Duplikate")

# %% 
# ========== Werksdaten 2NF ==========

df = tabellen["werksdaten"].drop_duplicates()
print(f"Original rows: {len(tabellen["werksdaten"])}")
print(f"Rows after dropping duplicates: {len(df)}")

# show that Artikelnummer alone is not unique
print(f"Zeilen gesamt:         {len(df)}")
print(f"Eindeutige Artikelnr.: {df['Artikelnummer'].nunique()}")
print()

combos = [
    ["Artikelnummer"],
    ["Artikelnummer", "Werk"],
    ["Artikelnummer", "Werk", "Lagerort"]
]
for cols in combos:
    dups = df.duplicated(subset=cols).sum()
    print(f"{cols}: {dups} Duplikate")

df.duplicated(subset=["Artikelnummer", "Werk"]).sum()

df[df.duplicated(subset=["Artikelnummer", "Werk"])]

# %%

def find_pk_conflicts(df: pd.DataFrame, pk: list[str]) -> pd.DataFrame:
    df_clean = df.drop_duplicates()
    conflicts = df_clean[df_clean.duplicated(subset=pk, keep=False)]
    
    results = []
    for key_vals, group in conflicts.groupby(pk):
        differing = [col for col in group.columns
                     if col not in pk and group[col].nunique() > 1]
        for _, row in group.iterrows():
            result = {col: row[col] for col in pk}
            result["konflikt_in"] = ", ".join(differing)
            for col in differing:
                result[col] = row[col]
            results.append(result)
    
    out = pd.DataFrame(results)
    
    int_cols = df.select_dtypes(include='int64').columns
    for col in int_cols:
        if col in out.columns:
            out[col] = out[col].astype('Int64')
    
    return out
#%%

pk_werksdaten = ["Artikelnummer", "Werk"]
conflicts = find_pk_conflicts(tabellen["werksdaten"], pk_werksdaten)
print(conflicts.to_string())
conflicts_styled =conflicts.style.hide(axis="index").set_caption("Konflikte in Werksdaten (Artikelnummer + Werk)").map(
    lambda v: "color: red;" if isinstance(v, str) and v != "" else "",
    subset=["konflikt_in"]
)
conflicts_styled

# #save conflicts to image for presentation with dataframe_image as dfioutput_subdir = get_output_dir(run_dir, "normalisierungsanalyse")
try:
    import dataframe_image as dfi
except ImportError:
    dfi = None
if config.get("export", {}).get("save_png", False) and dfi is not None:
    output_path = os.path.join(run_dir, "normalisierungsanalyse", "werksdaten_pk_conflicts.png")
    dfi.export(conflicts_styled, output_path, table_conversion="matplotlib", dpi=300)
    print(f"  Gespeichert: {os.path.basename(output_path)}")
# %%
