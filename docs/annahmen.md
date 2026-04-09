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

## Eindeutige Werte
Eindeutige Werte werden mit `dropna=True` berechnet (Standard `df.nunique()`).
NaN-Einträge werden nicht als eigene Kategorie gezählt, da fehlende Werte 
bereits separat in der Spalte "Fehlend" erfasst werden. Die beiden Metriken 
messen bewusst unterschiedliche Qualitätsdimensionen.



### Aufgabe 1
Documentation / domain knowledge
        │
        ▼
Declare PKs in config          ← human decision
        │
        ▼
Run 1NF checks                 ← fully automated
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