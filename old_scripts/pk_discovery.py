"""
pk_discovery.py — Primärschlüssel-Erkennung für alle Tabellenblätter.

Analysiert jede Tabelle und schlägt Primärschlüssel-Kandidaten vor.
Unterscheidet zwischen:
  - Einfachen Primärschlüsseln (eine Spalte)
  - Zusammengesetzten Primärschlüsseln / Composite Keys (mehrere Spalten)

Für jeden Kandidaten wird geprüft:
  - Eindeutigkeit (keine Duplikate)
  - Vollständigkeit (keine Nullwerte)
  - Semantische Eignung (basierend auf Spaltenname)

Erzeugt:
  - output/pk_discovery/<tabellenname>_pk_kandidaten.png  : Kandidatentabelle
  - output/pk_discovery/pk_zusammenfassung.png            : Tabellenübergreifende Zusammenfassung
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from itertools import combinations
from typing import Optional

import pandas as pd
import dataframe_image as dfi
from IPython.display import display


# ── Semantische Bewertung ─────────────────────────────────────────────────────
# Spaltennamen, die auf einen sinnvollen Schlüssel hinweisen → Bonus
_ID_MUSTER = [
    r'id$', r'_id$', r'nummer$', r'nr$', r'^id_', r'code$', r'key$',
]

# Spaltennamen, die auf zufällige Eindeutigkeit hinweisen → Abzug
_ABZUG_MUSTER = [
    r'name$', r'adresse$', r'telefon$',
    r'_ab$', r'_bis$', r'datum$',
    r'gewicht', r'laenge', r'breite', r'hoehe',
    r'preis', r'uvp', r'bestand',
]


def _semantik_score(spalte: str) -> int:
    """
    Bewertet, wie geeignet ein Spaltenname als PK-Komponente ist.
      +2  : ID-artiger Name (z.B. Artikelnummer, Lieferant_ID)
       0  : Neutral
      -1  : Wahrscheinlich zufällig eindeutig (z.B. Gültig_ab, Adresse)
    """
    col = spalte.lower()
    for muster in _ID_MUSTER:
        if re.search(muster, col):
            return 2
    for muster in _ABZUG_MUSTER:
        if re.search(muster, col):
            return -1
    return 0


# ── Datenklassen ──────────────────────────────────────────────────────────────

@dataclass
class PKKandidat:
    spalten: list[str]
    n_zeilen: int
    n_eindeutig: int
    n_nulls: int
    gueltig: bool          # eindeutig UND keine Nulls
    semantik_score: int
    hinweis: str = ""

    @property
    def n_duplikate(self) -> int:
        return self.n_zeilen - self.n_eindeutig

    def als_zeile(self) -> dict:
        """Gibt den Kandidaten als Dictionary für DataFrame-Export zurück."""
        return {
            "Spalten":        " + ".join(self.spalten),
            "Anzahl Spalten": len(self.spalten),
            "Eindeutig":      f"{self.n_eindeutig} / {self.n_zeilen}",
            "Duplikate":      self.n_duplikate,
            "Nulls":          self.n_nulls,
            "Score":          f"{self.semantik_score:+d}",
            "Status":         "✓ Gültig" if self.gueltig else "✗ Ungültig",
            "Hinweis":        self.hinweis,
        }


@dataclass
class PKBericht:
    tabelle: str           # var_name aus config (z.B. 'artikeldaten_grunddaten')
    anzeigename: str       # Sheet-Name aus config (z.B. 'Artikeldaten Grunddaten')
    n_zeilen: int
    kandidaten: list[PKKandidat] = field(default_factory=list)
    empfehlung: Optional[PKKandidat] = None

    def gueltige_kandidaten(self) -> list[PKKandidat]:
        return [k for k in self.kandidaten if k.gueltig]


# ── Kernlogik ─────────────────────────────────────────────────────────────────

def _pruefe_kandidat(df: pd.DataFrame, spalten: list[str]) -> PKKandidat:
    """Prüft eine Spaltenkombination als PK-Kandidaten."""
    n_zeilen    = len(df)
    n_eindeutig = df[spalten].drop_duplicates().shape[0]
    n_nulls     = int(df[spalten].isnull().any(axis=1).sum())
    gueltig     = (n_eindeutig == n_zeilen) and (n_nulls == 0)
    score       = sum(_semantik_score(s) for s in spalten)

    return PKKandidat(
        spalten=spalten,
        n_zeilen=n_zeilen,
        n_eindeutig=n_eindeutig,
        n_nulls=n_nulls,
        gueltig=gueltig,
        semantik_score=score,
    )


def _waehle_empfehlung(kandidaten: list[PKKandidat]) -> Optional[PKKandidat]:
    """
    Wählt den besten gültigen Kandidaten nach diesen Regeln:
      1. Muss gültig sein (eindeutig + keine Nulls)
      2. Minimale Anzahl Spalten (einfachster Schlüssel bevorzugt)
      3. Höchster Semantik-Score bei gleicher Spaltenanzahl
    """
    gueltige = [k for k in kandidaten if k.gueltig]
    if not gueltige:
        return None
    return sorted(gueltige, key=lambda k: (len(k.spalten), -k.semantik_score))[0]


def _entdecke_pk(
    df: pd.DataFrame,
    tabelle: str,
    anzeigename: str,
    ausschluss_spalten: list[str],
    max_composite: int,
) -> PKBericht:
    """
    Entdeckt PK-Kandidaten für eine einzelne Tabelle.

    Args:
        df:                 Der zu analysierende DataFrame.
        tabelle:            var_name aus config.
        anzeigename:        Anzeigename aus config.
        ausschluss_spalten: Spalten, die nicht als PK-Kandidaten geprüft werden.
        max_composite:      Maximale Anzahl Spalten im zusammengesetzten Schlüssel.
    """
    pruef_spalten = [s for s in df.columns if s not in ausschluss_spalten]
    bericht = PKBericht(
        tabelle=tabelle,
        anzeigename=anzeigename,
        n_zeilen=len(df),
    )
    kandidaten: list[PKKandidat] = []

    for breite in range(1, max_composite + 1):
        for kombo in combinations(pruef_spalten, breite):
            kandidat = _pruefe_kandidat(df, list(kombo))

            # Überspringe zusammengesetzte Schlüssel, wenn ein einfacherer
            # Teilschlüssel bereits gültig ist (Minimalitätsprinzip).
            if breite > 1:
                bereits_abgedeckt = any(
                    _pruefe_kandidat(df, list(teil)).gueltig
                    for teil_breite in range(1, breite)
                    for teil in combinations(kombo, teil_breite)
                )
                if bereits_abgedeckt:
                    continue

            kandidaten.append(kandidat)

    bericht.kandidaten = kandidaten
    bericht.empfehlung = _waehle_empfehlung(kandidaten)

    # Hinweis bei zufällig eindeutigen Kandidaten
    if bericht.empfehlung and bericht.empfehlung.semantik_score < 0:
        bericht.empfehlung.hinweis = (
            "Zufällig eindeutig in diesem Datensatz. "
            "Domänenwissen zur Bestätigung erforderlich."
        )

    return bericht


# ── Hauptfunktion ─────────────────────────────────────────────────────────────

def run_pk_discovery(
    tabellen: dict[str, pd.DataFrame],
    config: dict,
    project_dir: str,
) -> dict[str, PKBericht]:
    """
    Führt die PK-Erkennung für alle Tabellenblätter durch.

    Args:
        tabellen:    Dict mit var_name -> DataFrame (aus loader.py)
        config:      Geladene config.yaml
        project_dir: Projektverzeichnis

    Returns:
        Dict mit var_name -> PKBericht
    """
    output_dir = os.path.join(project_dir, "output", "pk_discovery")
    os.makedirs(output_dir, exist_ok=True)

    dpi       = config["export"]["bilder"]["dpi"]
    pk_config = config.get("pk_discovery", {})
    berichte: dict[str, PKBericht] = {}

    for var_name, df in tabellen.items():
        anzeigename = config["tabellen"][var_name]
        tab_cfg     = pk_config.get(var_name, {})
        ausschluss  = tab_cfg.get("ausschluss_spalten", [])
        max_comp    = tab_cfg.get("max_composite", 2)

        print(f"\n── {anzeigename} ──")

        bericht = _entdecke_pk(
            df=df,
            tabelle=var_name,
            anzeigename=anzeigename,
            ausschluss_spalten=ausschluss,
            max_composite=max_comp,
        )

        _drucke_bericht(bericht)
        _exportiere_kandidaten(bericht, output_dir, dpi)

        berichte[var_name] = bericht

    _exportiere_zusammenfassung(berichte, output_dir, dpi)

    return berichte


# ── Private Exportfunktionen ──────────────────────────────────────────────────

def _drucke_bericht(bericht: PKBericht) -> None:
    """Gibt den Bericht auf der Konsole aus."""
    gueltige   = bericht.gueltige_kandidaten()
    ungueltige = [k for k in bericht.kandidaten if not k.gueltig]

    if gueltige:
        print(f"  ✓ Gültige Kandidaten ({len(gueltige)}):")
        for k in sorted(gueltige, key=lambda x: (len(x.spalten), -x.semantik_score)):
            print(f"    [{' + '.join(k.spalten)}] "
                  f"Score: {k.semantik_score:+d} | "
                  f"Duplikate: {k.n_duplikate} | "
                  f"Nulls: {k.n_nulls}")
    else:
        print("  ✗ Keine gültigen PK-Kandidaten gefunden.")

    if ungueltige:
        print(f"  ✗ Ungültige Kandidaten ({len(ungueltige)}) — bester Annäherungskandidat:")
        bester = sorted(ungueltige, key=lambda k: (-k.n_eindeutig, k.n_nulls))[0]
        print(f"    [{' + '.join(bester.spalten)}] "
              f"Eindeutig: {bester.n_eindeutig}/{bester.n_zeilen} | "
              f"Duplikate: {bester.n_duplikate} | "
              f"Nulls: {bester.n_nulls}")

    if bericht.empfehlung:
        print(f"  ★ Empfehlung: {' + '.join(bericht.empfehlung.spalten)}")
        if bericht.empfehlung.hinweis:
            print(f"    Hinweis: {bericht.empfehlung.hinweis}")
    else:
        print("  ★ Empfehlung: Kein gültiger PK — Duplikate/Phantomdaten prüfen.")


def _exportiere_kandidaten(
    bericht: PKBericht,
    output_dir: str,
    dpi: int,
) -> None:
    """Exportiert die Kandidatentabelle als PNG."""
    if not bericht.kandidaten:
        return

    sortiert = sorted(
        bericht.kandidaten,
        key=lambda k: (not k.gueltig, len(k.spalten), -k.semantik_score),
    )

    df_export = pd.DataFrame([k.als_zeile() for k in sortiert])

    def _farbe_status(val: str) -> str:
        if val == "✓ Gültig":
            return "color: green; font-weight: bold;"
        if val == "✗ Ungültig":
            return "color: red;"
        return ""

    def _farbe_zahl(val) -> str:
        return "color: red;" if isinstance(val, int) and val > 0 else ""

    styled = (
        df_export.style
        .hide(axis="index")
        .set_caption(f"{bericht.anzeigename} — PK-Kandidaten")
        .map(_farbe_status, subset=["Status"])
        .map(_farbe_zahl, subset=["Duplikate", "Nulls"])
    )

    display(styled)

    dfi.export(
        styled,
        os.path.join(output_dir, f"{bericht.anzeigename}_pk_kandidaten.png"),
        table_conversion="matplotlib",
        dpi=dpi,
    )


def _exportiere_zusammenfassung(
    berichte: dict[str, PKBericht],
    output_dir: str,
    dpi: int,
) -> None:
    """Exportiert die tabellenübergreifende Zusammenfassung als PNG."""
    zeilen = []
    for var_name, bericht in berichte.items():
        emp = bericht.empfehlung
        zeilen.append({
            "Tabelle":        bericht.anzeigename,
            "Zeilen":         bericht.n_zeilen,
            "Empfohlener PK": " + ".join(emp.spalten) if emp else "— kein gültiger PK —",
            "PK-Spalten":     len(emp.spalten) if emp else "—",
            "Gültig":         "✓" if emp else "✗",
            "Hinweis":        emp.hinweis if emp and emp.hinweis else "",
        })

    df_zusammenfassung = pd.DataFrame(zeilen)

    def _farbe_gueltig(val: str) -> str:
        if val == "✓":
            return "color: green; font-weight: bold;"
        if val == "✗":
            return "color: red; font-weight: bold;"
        return ""

    styled = (
        df_zusammenfassung.style
        .hide(axis="index")
        .set_caption("PK-Erkennung — Zusammenfassung aller Tabellen")
        .map(_farbe_gueltig, subset=["Gültig"])
    )

    display(styled)

    dfi.export(
        styled,
        os.path.join(output_dir, "pk_zusammenfassung.png"),
        table_conversion="matplotlib",
        dpi=dpi,
    )

    print(f"\n── Zusammenfassung ──")
    print(df_zusammenfassung.to_string(index=False))
