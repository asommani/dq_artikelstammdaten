# Annahmen – Data Quality Analyse: Artikelstammdaten

**Projekt:** dq_artikelstammdaten  
**Autorin:** Anna Sommani  


Alle Annahmen werden hier transparent dokumentiert und erklärt. Wenn eine Annahme das Ergebnis eines bestimmten KPI oder Checks beeinflusst, wird dies explizit vermerkt.


---

## 1. Datenladung und Scope

**Scope der Pflichtfelder:** Im Aufgabenbrief werden sowohl "Nettogewicht" als auch "Nettgewicht" als Pflichtfelder genannt. Da "Nettgewicht" kein standardmäßiger deutscher Begriff ist und der Datensatz nur die Spalte `Nettogewicht in kg` enthält, wird dies als Tippfehler interpretiert. Beide Angaben werden als dasselbe Pflichtfeld verstanden.

**Fokus auf Grunddaten und Werksdaten:** Gemäß Aufgabenstellung fokussiert sich die Analyse auf Artikelstammdaten (Grunddaten und Werksdaten). Unterstützende Tabellen (Preise, Kategorisierung, Lieferantendaten) werden für Kontextprüfungen (Preisvalidierung, Referenzintegrität) einbezogen, aber die Vollständigkeit von Pflichtfeldern wird ausschließlich für Grunddaten definiert.

**Validierung der Sheet-Namen:** Beim Laden führt `loader.py` einen exakten Abgleich zwischen den in `config.yaml` definierten Sheet-Namen und den tatsächlich in der Excel-Datei vorhandenen durch. Jede Abweichung führt unmittelbar zu einem Assertion Error.

---

## 2. Fehlende Werte

**Definition von "fehlend":** Ein Wert gilt als fehlend, wenn er eine der folgenden Bedingungen erfüllt:

- `NaN` / `None` : systemseitig fehlender Wert  
- Leerer String `""` : leere Eingabe  
- String nur aus Whitespaces `" "`, `" "` usw. : enthält ausschließlich Leerzeichen, Tabs oder Zeilenumbrüche  

Alle drei Fälle sind für nachgelagerte Prozesse funktional äquivalent zu fehlend. Die Berücksichtigung von Strings, die nur aus Whitespaces bestehen, ist durch ein häufiges Artefakt manueller Dateneingabe in MDM- und ERP-Systemen motiviert: Anwender, die durch Eingabefelder navigieren (z. B. mit der Tab-Taste), können versehentlich ein Feld mit einem Leerzeichen füllen, anstatt es wirklich leer zu lassen. Insbesondere in SAP-Systemen, in denen Zeichenfelder (`CHAR`) auf eine feste Länge mit Leerzeichen aufgefüllt werden, werden solche Werte als Whitespaces gespeichert und nicht als Null. Beim Export nach Excel und Laden in pandas erscheinen diese Zellen als nicht-null (`df.isnull()` ergibt `False`) und bleiben bei einem reinen `NaN`-Check unentdeckt. Ein reiner `NaN`-Check würde daher fehlende Werte unterschätzen und die Datenqualität überschätzen.

**Technische Umsetzung:** Leere Strings und Strings, die nur aus Whitespaces bestehen, werden mittels Regex `^\s*$` auf Textspalten (`dtype=object`) erkannt und zum `NaN`-Count hinzugefügt. Dies ist zentral in `utils.py → fehlend_pro_spalte()` implementiert und wird einheitlich über alle Checks hinweg angewendet: Vollständigkeit, Eindeutigkeit, Konsistenz.

**Anwendung:** Verwendet in: `overview.py`, `kpi.py` (Vollständigkeit, Eindeutigkeit, Konsistenz Einheit), `reporter.py` (Vokabularvalidität).  
**Nicht angewendet in:** `check_konsistenz_masse`: Dimensionsspalten sind `float64`; Whitespaces können dort nicht auftreten, daher ist ein `NaN`-Check ausreichend.

**Empirischer Befund:** Im aktuellen Datensatz wurden keine leeren oder nur aus Whitespaces bestehenden Einträge gefunden (Anzahl = 0). Die Logik bleibt für zukünftige Datenexports bestehen.

---

## 3. Vollständigkeit (Completeness KPI)

**Nenner der Rate:** Die Vollständigkeitsrate wird als `1 - (missing / n_total)` pro Feld berechnet, und die Gesamtrate über alle Pflichtfelder hinweg als `1 - (total_missing / (n_rows x n_fields))`. Dies folgt der Microsoft-Purview-Konvention: `score = passed / (passed + failed + empty)`, d. h. fehlende Werte reduzieren den Score und werden nicht ausgeschlossen.

**Scope der Pflichtfelder:** Pflichtfelder sind ausschließlich für `artikeldaten_grunddaten` definiert (13 Felder, wie in `rules.yaml` aufgeführt). Für Werksdaten oder Lieferantendaten sind keine Pflichtfelder definiert.

---

## 4. Eindeutigkeit (Uniqueness KPI)

**Nenner der Rate:** Die Eindeutigkeitsrate wird als `n_unique / n_total` berechnet, wobei `n_total` auch Zeilen mit fehlenden Werten umfasst. Dies entspricht der Vollständigkeitslogik: Eine fehlende Artikelnummer ist ein Datenqualitätsproblem und wird nicht ausgeschlossen.

**Duplikatzählung:** Duplikate werden mittels pandas `duplicated()` identifiziert, nachdem leere/Whitespace-Strings bereinigt wurden (`replace(r"^\s*$", pd.NA)`). Die `eindeutig_rate` bezieht sich auf die Anzahl unterschiedlicher nicht-null Werte relativ zur Gesamtanzahl der Zeilen.

---
## 5. Konsistenz Maße (Dimension Consistency KPI)

**Join-Key:** Werksdaten werden über den zusammengesetzten Schlüssel `[Artikelnummer, Werk]` mit den Grunddaten verknüpft (Inner Join). Es werden nur Datensätze verglichen, die in beiden Tabellen vorhanden sind.

**Deduplikation der Werksdaten:** Vor dem Vergleich werden die Werksdaten in zwei Schritten dedupliziert:

1. Entfernen exakter Duplikate (`drop_duplicates()` über alle Spalten).
    
2. Entfernen verbleibender Duplikate auf Basis des zusammengesetzten Schlüssels `[Artikelnummer, Werk]` (Beibehaltung der ersten Vorkommens).
    

Dies ist eine bewusste Designentscheidung: Konflikte in Nicht-Dimensionsfeldern (z. B. unterschiedliche Disponenten für denselben Artikel+Werk-Schlüssel) werden als separates Datenqualitätsproblem behandelt (siehe Check Werksdaten Konflikte) und nicht in den Konsistenz-KPI übernommen. Der Konsistenz-KPI beantwortet ausschließlich die Frage: Wie viele der vergleichbaren Paare stimmen überein?

**Ausschluss von Nullwerten:** Zeilen, in denen eine der Dimensionsspalten (`Laenge_cm`, `Breite_cm`, `Hoehe_cm` in den Grunddaten oder die entsprechenden Spalten in den Werksdaten) den Wert `NaN` enthält, werden vom Vergleich ausgeschlossen und separat als `ausgeschlossen` ausgewiesen. Fehlende Werte sind ein Problem der Vollständigkeit, nicht der Konsistenz. Eine doppelte Bestrafung desselben Fehlers über zwei KPIs würde das Gesamtbild verzerren. Dies entspricht gängiger Praxis in der Industrie (Microsoft Purview, DQOps).

**Nenner der Rate:** Die Konsistenzrate verwendet `n_comparable` (nicht `n_gesamt`) als Nenner. Dies ist keine Designentscheidung, sondern eine mathematische Notwendigkeit, da ein Vergleich ohne beide vorhandene Werte nicht möglich ist.

**Abweichungsschwelle und Vergleichslogik:** Die relative Abweichung wird für jede der drei Dimensionen (Länge, Breite, Höhe) separat berechnet als `|grund - werk| / grund`. Anschließend wird pro Artikel das Maximum dieser drei Abweichungen gebildet (`max(axis=1)`), und ein Artikel wird als inkonsistent klassifiziert, wenn dieses Maximum strikt größer als 10% ist (`> 0.10`, nicht `>= 0.10`). Dies ist in `rules.yaml → schwellenwerte.konsistenz_abweichung_max` konfiguriert.

**Behandlung von Division durch Null:** Wenn ein Dimensionswert in den Grunddaten exakt `0` ist, wird die relative Abweichung für dieses Paar auf `NaN` gesetzt (mittels `np.where`) und dieses Paar von der Maximum-Abweichungsberechnung ausgeschlossen. Dadurch werden Division-durch-Null-Fehler vermieden und eine willkürliche Klassifikation von Datensätzen mit Null-Dimensionen verhindert.

**Sanity-Check:** Eine boolesche Spalte `_sanity_check` ist im Output enthalten und überprüft, dass `ausgeschlossen + konsistent + inkonsistent == paare_gesamt`. Dies wird zur Nachvollziehbarkeit beibehalten.

---
## 6. Konsistenz Einheit Maße (Unit Consistency KPI)

**Scope:** Die Aufgabenstellung verlangt die Prüfung der Konsistenz von Maßeinheiten (cm vs. mm). Dies wurde so interpretiert, dass es ausschließlich auf Längen- beziehungsweise Dimensionsangaben anzuwenden ist und nicht auf Mengeneinheiten (z. B. g, ml, kg in `Mengeneinheit`).

Bezüglich der tatsächlich prüfbaren Spalten gilt: Nur die Werksdaten enthalten eine explizite Spalte für Maßeinheiten (`Mass_Einheit`) und sind daher das einzige Ziel dieses KPIs. Für die Grunddaten ist die Situation differenzierter. Im Aufgabenbrief (Seite 2) wird `Verpackungseinheit` als Feld der Grunddaten aufgeführt, diese Spalte ist jedoch im tatsächlichen Datensatz nicht vorhanden. Stattdessen enthalten die Grunddaten eine nicht dokumentierte Spalte `Verpackungsart` (z. B. "Flasche, Mehrweg"), die die Verpackungsart beschreibt und keine Maßeinheit darstellt. Die einzige einheitenbezogene Spalte in den Grunddaten ist `Mengeneinheit`, die sich auf Mengeneinheiten (g, ml, kg) bezieht und nicht auf physische Dimensionen. Sie liegt daher außerhalb des Scopes dieser Prüfung.

Daraus folgt, dass der KPI ausschließlich auf `Mass_Einheit` in den Werksdaten berechnet wird, wobei `["cm"]` als einzig gültiger Wert definiert ist. Eine analoge Prüfung für Grunddaten ist auf Basis der vorhandenen Daten nicht möglich.

**Gültige Werte:** Die gültige Einheit ist `["cm"]`, definiert in `rules.yaml → gueltige_werte.mass_einheit`. Jeder andere Wert (z. B. `mm (falsch)`) wird als ungültig klassifiziert.

**Nenner der Rate:** Sowohl `valid_rate` als auch `invalid_rate` verwenden `n_gesamt` (Gesamtanzahl der Zeilen) als Nenner, konsistent mit der Vollständigkeitskonvention.

---
## 7. 1NF-Atomaritätsprüfung (Normalisierung)

**Methode:** Der Check markiert jede String-Zelle, die eines der konfigurierten Trennzeichen (`,`, `;`, `/`, `(`, `)`) enthält, als potenziellen Kandidaten für einen Verstoß gegen die 1NF. Es handelt sich hierbei ausschließlich um Kandidaten; zur endgültigen Bewertung, ob es sich um einen tatsächlichen Verstoß oder um ein legitimes zusammengesetztes Label handelt, ist menschliche Beurteilung erforderlich.

**Scope:** Eine Analyse der 2NF und 3NF kann nicht vollständig automatisiert werden und erfordert Domänenwissen. Die vollständige, fallspezifische Normalisierungsanalyse, einschließlich der Bewertung der markierten Kandidaten, der Analyse funktionaler Abhängigkeiten sowie der abgeleiteten Empfehlungen, ist in `diagnostics/normalization_analysis.py` und in der zugehörigen Präsentation dokumentiert und umgesetzt.

**Runtime-Flag:** Die 1NF-Prüfung wird über das Boolean-Flag `normalization.check_1nf` in `config.yaml` gesteuert. Sie ist standardmäßig deaktiviert (`false`), da es sich um einen schema-bezogenen, einmaligen Check handelt und nicht um einen Bestandteil der regelmäßig ausgeführten Data-Quality-Pipeline.

---

## 8. Preisvalidierung (Price Validation)

**Sentinel-Werte:** Die expliziten Sentinel-Werte `9999.99` und `0.01` werden als bekannte Platzhalterpreise markiert (konfiguriert in `rules.yaml → preisvalidierung.sentinel_werte`).

**Preisbereich:** Preise außerhalb des Bereichs `[0.10, 999.99]` EUR (nach Entfernung der Sentinel-Werte) werden als außerhalb des gültigen Bereichs klassifiziert. Die Untergrenze (`preis_min = 0.10`) dient dazu, nahezu nullwertige Nicht-Sentinel-Preise zu erkennen. Die Obergrenze (`preis_max = 999.99`) identifiziert unplausible Ausreißer. Beide Schwellenwerte sind in `rules.yaml → schwellenwerte` konfiguriert.

**Kategorisierung ungültiger Werte:** Sentinel-Werte, Preise außerhalb des gültigen Bereichs sowie ungültige Währungen werden als separate Masken-Kategorien erkannt und zu einer gemeinsamen `mask_invalid` zusammengeführt. Ein Preis wird dabei nur einmal gezählt, auch wenn er in mehrere Kategorien fällt (Union-Semantik).

**Gültige Währungen:** Als gültige Währung ist ausschließlich `EUR` definiert (`rules.yaml → gueltige_werte.waehrung`). Andere im Datensatz vorkommende Währungen werden als ungültig markiert. dm-drogerie markt ist in 14 europäischen Märkten tätig, jeweils mit potenziell unterschiedlichen lokalen Währungen. Da die Aufgabenstellung jedoch keine Multi-Währungslogik spezifiziert, wird `EUR` als einzige gültige Währung für diesen Datensatz angenommen. Zusätzlich lassen sich die konkret im Datensatz gefundenen ungültigen Währungen auch operativ ausschließen: dm ist weder in der Schweiz noch in Indien tätig, wodurch `CHF` und `INR` unabhängig von einer allgemeinen Währungspolitik als ungültig gelten.

---
## 9. Referenzintegrität (Referential Integrity)

**Referentielle Child-to-Parent-Integritätsprüfung:** Der Check überprüft, ob jede `Artikelnummer` in `Kategorisierung` in den `Grunddaten` existiert. Vor dem Vergleich werden Duplikate und Nullwerte aus `Kategorisierung` entfernt, da mehrere Zeilen auf denselben Artikel verweisen können (z. B. mehrere Kategoriezuordnungen pro Artikel). Die Prüfung erfolgt daher auf Ebene eindeutiger Artikelnummern und nicht auf Basis aller Zeilen.

Von den eindeutigen Artikelnummern in `Kategorisierung` sind 147 korrekt in den `Grunddaten` referenziert, während 176 keine Entsprechung haben. Diese 176 stellen Orphan-Records dar, also Artikelnummern, die in `Kategorisierung` vorkommen, aber keinen entsprechenden Eintrag in den Artikelstammdaten besitzen. Dies stellt ein erhebliches Problem der referenziellen Integrität dar, da ein großer Teil der Kategorisierungsdaten keinem bekannten Artikel zugeordnet werden kann.

Die Orphan-Rate wird als `n_orphan / n_unique` berechnet (176 / 323 = 54.5%) und nicht auf Basis der Gesamtanzahl der Zeilen.

---
## 10. Werksdaten Konflikte (Werksdaten Conflicts)

**Zweistufige Deduplikation:** Der Konflikt-Check unterscheidet explizit zwischen:

1. **Exakten Duplikaten:** Identische Zeilen über alle Spalten hinweg. Diese können ohne Risiko entfernt werden.
    
2. **Konflikten:** Zeilen, die denselben zusammengesetzten Schlüssel `[Artikelnummer, Werk]` teilen, sich jedoch in mindestens einer Nicht-Schlüssel-Spalte unterscheiden. Es wurden drei Konflikte identifiziert: A0068/Werk Nord (unterschiedlicher `Status`: Freigegeben vs. Ausgelistet), A0093/Werk Süd (unterschiedliche `Lieferant_ID`: 1 vs. 19) und A0391/Werk Ost (unterschiedliche `Lieferant_ID`: 17 vs. 19). Diese stellen ein echtes Datenqualitätsproblem dar und erfordern Domänenwissen zur Auflösung.
    

Diese Unterscheidung ist wesentlich: Exakte Duplikate sind ein Fehler im Data Management (z. B. doppelte Inserts), während Konflikte auf inkonsistente Stammdaten über verschiedene Systeme oder Erfassungspunkte hinweg hinweisen.

**Auflösungsstrategie im Konsistenz-KPI:** Wenn die Werksdaten Konflikte enthalten, wird für die Konsistenzprüfung der Maße die erste Vorkommens nach Entfernung exakter Duplikate verwendet. Es wird kein Versuch unternommen zu bestimmen, welcher der konfligierenden Werte „korrekt“ ist, da dies Domänenwissen erfordert. Auffällig ist, dass in allen drei Konfliktfällen die Dimensionsspalten (`Laenge_cm_werk`, `Breite_cm_werk`, `Hoehe_cm_werk`) identisch sind, sodass diese Konflikte keinen Einfluss auf das Ergebnis des Konsistenz Maße KPI haben.

---
## 11. Plausibilitätscheck Maße (Dimension Plausibility)

**Regel:** Eine Zeile wird als implausibel klassifiziert, wenn ein Maßwert (Länge, Breite, Höhe) `<= 0` ist (Untergrenze) oder den in `rules.yaml → plausibilitaet_masse.implausibel_max` definierten Schwellenwert überschreitet (Obergrenze, gespeichert in der Ausgabespalte `impl_max_threshold`). Beide Prüfungen werden auf die Maßspalten der Grunddaten und Werksdaten angewendet. Die beiden Verletzungstypen werden separat ausgewiesen als `impl_min_n` (Anzahl `<= 0`-Verletzungen) und `impl_max_n` (Anzahl `> impl_max_threshold`-Verletzungen); eine Zeile, die durch eine der beiden Bedingungen geflagt wird, zählt als eine implausible Zeile in `tot_implausibel` (keine Doppelzählung).

**Behandlung fehlender Werte:** Zeilen mit einem `NaN`-Maßwert werden zunächst von der Plausibilitätsprüfung ausgeschlossen (als `fehlend` ausgewiesen). Nur Nicht-Null-Zeilen werden auf die Bedingungen `<= 0` und `> impl_max_threshold` geprüft.

**Nenner der Rate:** `tot_implausibel_rate` und `plausibel_rate` verwenden `n_gesamt` (Gesamtanzahl Zeilen) als Nenner.

---
## 12. GTIN / EAN-13 Formatprüfung

**Regel:** GTINs werden zunächst in Integer konvertiert, anschließend in Strings umgewandelt und mittels `str.zfill(13)` auf 13 Stellen mit führenden Nullen aufgefüllt. Die Integer-Konvertierung entfernt den durch die Speicherung als Floating-Point in Excel entstandenen `.0`-Suffix. Das Zero-Padding stellt korrekt einzelne führende Nullen wieder her, die sonst durch die Integer-Konvertierung verloren gehen würden. Anschließend wird die Länge exakt auf 13 Zeichen geprüft, wie es der EAN-13-Standard verlangt.

**Prüfziffernvalidierung:** Die EAN-13-Prüfziffer wird nicht validiert, es wird ausschließlich die Anzahl der Ziffern geprüft. Eine vollständige Validierung der Prüfziffer wäre eine weiterführende, strengere Erweiterung.

**Sentinel-GTINs:** Sentinel-GTIN-Werte sind in `rules.yaml` definiert (ein Sentinel-Wert, `9999999999999`, der in diesem Datensatz für Artikel A0500 identifiziert wurde). Sentinel-Werte werden von der Formatprüfung ausgeschlossen und als separate Kategorie ausgewiesen und konsistent mit der Preisvalidierung zum `tot_invalid` gezählt.

**Umgang mit Nullwerten:** Null-GTINs werden von allen Prüfungen ausgeschlossen und separat als `fehlend` ausgewiesen. Drei Artikel weisen eine fehlende GTIN auf: A0045, A0249, A0440.

---
## 13. Konvention zur Ratenberechnung (Zusammenfassung)

Alle Raten (mit Ausnahme von `konsistenz_masse`) folgen der **Microsoft-Purview-Konvention**:

> `rate = passed / (passed + failed + empty)`  
> Nenner = `n_gesamt` (Gesamtanzahl der Zeilen, einschließlich fehlender Werte)

Ein fehlender Wert wird aus Sicht des Data Managements als ebenso problematisch betrachtet wie ein ungültiger Wert, da beide dazu führen, dass der Datensatz für nachgelagerte Prozesse nicht nutzbar ist.

**Ausnahme - Konsistenz Maße:** Verwendet `n_comparable` als Nenner (mathematisch erforderlich, siehe Abschnitt 5).

---

## 14. Vokabularvaliditätsprüfung

**Grundlegende Vokabularvaliditätsprüfung:** Die Annahmen zur Validierung kontrollierter Vokabulare für `Mengeneinheit`, `Temperaturzone` und `Pfandpflicht` sind in `rules.yaml` definiert. Dieser Check ist strukturell identisch mit der Prüfung der Konsistenz von Maßeinheiten, da in beiden Fällen überprüft wird, ob die Werte einer Spalte zu einer vordefinierten Menge gehören. Daher wird dieselbe zugrunde liegende Funktion `check_konsistenz_einheit_masse` wiederverwendet, wobei unterschiedliche Konfigurationen über `rules.yaml` übergeben werden. Dieser Check ist standardmäßig deaktiviert (`validitaet_vokabular: false` in `config.yaml`) und wird als zusätzlicher diagnostischer Check behandelt, da die Aufgabenstellung keine explizite Validierung kontrollierter Vokabulare fordert.

**Einschränkungen:** Die Vokabularvaliditätsprüfung (`run_validitaet_vokabular`) identifiziert Werte, die nicht zu den in `rules.yaml` definierten kontrollierten Vokabularen gehören. Sie erkennt jedoch keine semantischen Fehlzuordnungen, also Fälle, in denen ein Wert formal gültig ist, aber inhaltlich falsch verwendet wurde. Das folgende Kapitel listet Inkonsistenzen auf, die durch manuelle Analyse identifiziert wurden und außerhalb des Scopes der automatisierten Checks liegen.

---

## 15. Weitere beobachtete Datenprobleme außerhalb der automatisierten Checks in den Grunddaten

Die folgenden Probleme wurden durch manuelle Analyse identifiziert und sind nicht Teil der automatisierten Pipeline. Dies liegt entweder daran, dass im Aufgabenbrief keine formale Regel definiert wurde oder dass der Check eine spaltenübergreifende Validierung erfordern würde, die über den aktuellen Rahmen hinausgeht.

**Artikelnummer-Format:** Es wird keine automatisierte Formatvalidierung für Artikelnummern durchgeführt, da im Aufgabenbrief keine entsprechende Regel definiert ist. Die manuelle Analyse zeigt zwei auffällige Einträge in den Grunddaten: `A99999` (fünf Ziffern statt der erwarteten vier) und `AAAAA` (keine Ziffern, entspricht nicht dem erkennbaren Muster `A` + 4 Ziffern). Diese sind vermutlich Eingabefehler, können jedoch ohne formal definierte Regel nicht automatisch erkannt werden. Eine solche Regel (z. B. Regex `^A\d{4}$`) könnte einfach über `rules.yaml` ergänzt werden.

**Falsche Warengruppen-Zuordnung:** Drei Artikel sind eindeutig falschen Warengruppen zugeordnet: A0285 (Chips Oriental) ist unter Getränke geführt, A0393 (Joghurt mild) unter Obst & Gemüse und A0400 (Reisnudeln) unter Fleisch & Wurst. Dies sind plausible Eingabefehler, die durch den aktuellen automatisierten Vokabular-Check nicht erkannt werden, da die zugewiesenen Werte formal gültige Warengruppen darstellen.

**Inkonsistenzen zwischen Warengruppe und Temperaturzone:** Mehrere Artikel weisen unplausible Kombinationen von Warengruppe und Temperaturzone auf. A0014 (Limonade, Getränke) ist als Tiefkühl klassifiziert, was für ein Standardgetränk nicht plausibel ist. Drei Tiefkühlartikel (A0089 Pommes TK gewellt, A0373 Pizza TK, A0473 Pommes TK geschnitten) sind als Kühl klassifiziert oder haben keine Temperaturzone, obwohl Tiefkühlprodukte per Definition Tiefkühl erfordern. Zusätzlich sind 14 Molkereiprodukte als Ambient klassifiziert, obwohl Milchprodukte üblicherweise gekühlt gelagert werden.

**Mengeneinheit semantisch falsch für Kategorie:** Mehrere Obst & Gemüse Artikel haben `Mengeneinheit = ml` (z. B. Kartoffel, Banane), was semantisch nicht korrekt ist, da frische Produkte üblicherweise in g oder als Stückeinheiten gemessen werden und nicht in Millilitern.

**Pfandpflicht = Ja bei Nicht-Getränken:** Im deutschen Markt gilt Pfand primär für Getränkeverpackungen und bestimmte Glasverpackungen (z. B. Joghurtgläser). Es wurden jedoch mehrere Artikel identifiziert, bei denen eine Pfandpflicht schwer nachvollziehbar ist, die aber dennoch `Pfandpflicht = Ja` aufweisen, darunter Kartoffel Bio (A0004), Karotte Bio (A0068), Keks Bio (A0077), Croissant (A0082) und Olivenöl (A0403) sowie weitere.

**Hinweis zum Scope:** Diese Befunde werden hier als bekannte Einschränkungen der automatisierten Pipeline dokumentiert. Die Erkennung semantischer Fehlzuordnungen im großen Maßstab würde eine **spaltenübergreifende Regelvalidierung** erfordern (z. B. wenn Warengruppe = Tiefkühlkost, dann muss Temperaturzone = Tiefkühl sein) oder eine Anreicherung mit externen Referenzdaten. Beide Ansätze sind als Erweiterung des bestehenden Frameworks über `rules.yaml` umsetzbar.