Die Aufgabenstellung nennt sowohl 'Nettogewicht' als auch 'Nettgewicht' als Pflichtfeld. Da 'Nettgewicht' kein standarddeutsches Wort ist und im Datensatz nur die Spalte 'Nettogewicht in kg' existiert, wird angenommen, dass es sich um einen Tippfehler in der Aufgabenstellung handelt. Beide Angaben werden als dasselbe Pflichtfeld 'Nettogewicht in kg' behandelt.


## Fehlende Werte
Als fehlender Wert ("Fehlend") wird gezählt:
- `NaN` / `None` — systemseitig fehlende Werte
- Leere Strings `""` — inhaltlich leere Einträge
- Whitespace-only Strings `" "`, `"  "` etc. — Einträge die nur Leerzeichen enthalten

Begründung: Alle drei Fälle sind für nachgelagerte Prozesse funktional 
äquivalent zu fehlenden Werten — sie enthalten keine nutzbare Information. 
Eine reine NaN-Prüfung würde diese Fälle übersehen und die Datenqualität 
zu positiv bewerten.

Technische Umsetzung: Leere und Whitespace-Einträge werden mittels 
`str.strip() == ""` auf Text-Spalten (dtype=object) erkannt und zur 
NaN-Anzahl addiert.

Hinweis: In diesem Datensatz wurden keine leeren oder Whitespace-Einträge 
gefunden (Wert = 0). Die Prüfung bleibt im Script erhalten für zukünftige 
Datenexporte.

Leere Strings (`""`), Whitespace-only Strings (`" "`) und verwandte Sonderzeichen (Tabs, Zeilenumbrüche) werden mittels Regex `^\s*$` erkannt und funktional als fehlende Werte behandelt. Diese Konvention gilt einheitlich für alle Berechnungen (Vollständigkeit, Eindeutigkeit, Konsistenz) und ist in `utils.py` (`fehlend_pro_spalte`) zentral implementiert.


### Aufgabe 1
Documentation / domain knowledge
        │
        ▼
Declare PKs in config          ← human decision
        │
        ▼
Run 1NF checks                 ←  automated flagging
        │
   Pass? ──No──► Report violation, investigate root cause
        │
       Yes
        ▼
Run 2NF checks                 ← suspects from domain knowledge
        │                         confirmed by FD scoring
   Pass? ──No──► Report violation
        │
       Yes
        ▼
Run 3NF checks                 ← suspects from domain knowledge
        │                         confirmed by FD scoring
   Pass? ──No──► Report violation
        │
       Yes
        ▼
Database is normalized ✓

#%%

1Nf check:
artikeldaten_grunddaten got 3 types of value flagged:
1 time "Milch 1,5%" in Artikelname
2 times "Croissant klein, schokoladig" in Artikelname
13 times "Flasche, Mehrweg" in Verpackungsart
I think that the only value that is actually not respecting atomiticity (1NF) is the "Flasche, Mehrweg" 


"Die Normalformanalyse ist eine einmalige Schema-Prüfung und wird als separates Skript geführt. Die laufende Datenqualitätsmessung erfolgt automatisiert über run_analysis.py."


#### Augabe 2: Konistenz
> Fehlende Werte (NaN) in Maßspalten werden bei der Konsistenzprüfung (Grunddaten vs. Werksdaten) aus dem Vergleich ausgeschlossen und separat als `ausgeschlossen` ausgewiesen. Dies entspricht dem Industriestandard (u.a. Microsoft Purview, DQOps): fehlende Werte sind ein Problem der **Vollständigkeit**, nicht der **Konsistenz**. Eine doppelte Bestrafung desselben Defekts in zwei verschiedenen KPIs würde das Gesamtbild verzerren. Der Konsistenz-KPI beantwortet ausschließlich die Frage: „Von den vergleichbaren Paaren — wie viele stimmen überein?"


Blank/whitespace treated as missing via ^\s*$
Nulls excluded from consistency check (not double-counted)
Werksdaten deduplicated automatically (conflicts only in non-dimension fields)
Abweichung strictly > 0.10, not >=
Pflichtfelder only defined for Grunddaten per brief


Sowohl Grunddaten (`Laenge_cm`, `Breite_cm`, `Hoehe_cm`) als auch Werksdaten (`Laenge_cm_werk`, `Breite_cm_werk`, `Hoehe_cm_werk`) kodieren die Einheit `cm` implizit im Spaltennamen. Nur Werksdaten führt zusätzlich eine explizite Einheitenspalte `Mass_Einheit`, die geprüft werden kann und tatsächlich fehlerhafte Werte (`mm (falsch)`) enthält. Die Einheitlichkeitsprüfung bezieht sich ausschließlich auf diese Spalte. Für Grunddaten ist keine analoge Prüfung möglich, da keine separate Einheitenspalte für Maße/Längen existiert.