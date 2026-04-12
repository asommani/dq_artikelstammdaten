# Assumptions and Methodology – Data Quality Analysis: Article Master Data

**Project:** dq_artikelstammdaten  
**Author:** Anna Sommani  

This document transparently records all assumptions, methodological decisions, and known limitations of the analysis. Where a decision affects the outcome of a specific KPI or check, the rationale is explained explicitly.

---

## 1. Data Loading and Scope

**Scope of mandatory fields (Pflichtfelder):** The task brief specifies both "Nettogewicht" and "Nettgewicht" as mandatory fields. Since "Nettgewicht" is not a standard German word and the dataset contains only the column `Nettogewicht in kg`, this is treated as a typographical error in the brief. Both references are interpreted as the single mandatory field `Nettogewicht in kg`.

**Focus on Grunddaten and Werksdaten:** Per the task brief, the analysis focuses on article master data (Grunddaten and Werksdaten). The supporting tables (Preise, Kategorisierung, Lieferantendaten) are included for contextual checks (price validation, referential integrity) but mandatory field completeness is only defined for Grunddaten.

**Sheet name validation:** On load, `loader.py` performs an exact match between the sheet names declared in `config.yaml` and those present in the Excel file. Any mismatch raises an assertion error immediately.

---

## 2. Missing Values

**Definition of "missing":** A value is counted as missing if it is any of the following:

- `NaN` / `None` : system-level missing value
- Empty string `""` : blank entry
- Whitespace-only string `" "`, `" "`, etc. : entry containing only spaces, tabs, or newline characters

All three cases are functionally equivalent to missing for downstream processes. The inclusion of whitespace-only strings is motivated by a common artifact of manual data entry in MDM and ERP systems: operators navigating through input fields (e.g., via tab-key) may inadvertently submit a field containing only a space character rather than leaving it truly empty. In SAP-based systems in particular, where character-type fields (`CHAR`) are padded to a fixed length with blanks, such entries are stored as whitespace strings rather than nulls. When exported to Excel and loaded into pandas, these cells appear non-null (`df.isnull()` returns `False`) and are invisible to a standard `NaN` check. A pure `NaN` check would therefore undercount missing values and overstate data quality.

**Technical implementation:** Empty and whitespace-only strings are detected via regex `^\s*$` applied to text columns (`dtype=object`) and added to the `NaN` count. This is centrally implemented in `utils.py → fehlend_pro_spalte()` and applied uniformly across all checks: Vollständigkeit, Eindeutigkeit, Konsistenz.

**Application:** Used in: `overview.py`, `kpi.py` (Vollständigkeit, Eindeutigkeit, Konsistenz Einheit), `reporter.py` (vocabulary validity).  
**Not applied in:** `check_konsistenz_masse`: dimension columns are `float64`; whitespace strings cannot occur there, so a `NaN` check is sufficient.

**Empirical finding:** No empty or whitespace-only entries were found in the current dataset (count = 0). The logic remains in place for future data exports.

---

## 3. Vollständigkeit (Completeness KPI)

**Rate denominator:** Completeness rate is computed as `1 - (missing / n_total)` per field, and the overall rate is computed over all mandatory fields combined: `1 - (total_missing / (n_rows x n_fields))`.

**Mandatory fields scope:** Mandatory fields are only defined for `artikeldaten_grunddaten` (13 fields, as listed in `rules.yaml`). No mandatory fields are declared for Werksdaten or Lieferantendaten.

---

## 4. Eindeutigkeit (Uniqueness KPI)

**Rate denominator:** The uniqueness rate is computed as `n_unique / n_total`, where `n_total` includes rows with missing values. This is consistent with the Vollständigkeit convention: a missing Artikelnummer is a data quality problem, not a row to be silently excluded.

**Duplicate counting:** Duplicates are identified using pandas `duplicated()` after stripping empty/whitespace strings (via `replace(r"^\s*$", pd.NA)`). The `eindeutig_rate` reflects the number of distinct non-null values relative to total rows.

---

## 5. Konsistenz Maße (Dimension Consistency KPI)

**Join key:** Werksdaten are joined to Grunddaten on the composite key `[Artikelnummer, Werk]` (inner join). Only records present in both tables are compared.

**Werksdaten deduplication:** Before comparison, Werksdaten are deduplicated in two steps:
1. Remove exact duplicate rows (`drop_duplicates()` across all columns).
2. Remove remaining duplicates on the composite key `[Artikelnummer, Werk]` (keeping first occurrence).

This is a deliberate design choice: conflicts in non-dimension fields are treated as a separate data quality issue (see Werksdaten Konflikte check) and are not propagated into the consistency KPI. The consistency KPI answers only: 'Of the comparable pairs, how many agree?'

**Null exclusion:** Rows where any dimension column (`Laenge_cm`, `Breite_cm`, `Hoehe_cm` in Grunddaten or their Werksdaten counterparts) is `NaN` are excluded from comparison and reported separately as `ausgeschlossen`. Missing values are a problem of Vollständigkeit, not Konsistenz. Double-penalizing the same defect across two KPIs would distort the overall picture. This follows industry convention (Microsoft Purview, DQOps).

**Rate denominator:** The consistency rate uses `n_comparable` (not `n_gesamt`) as denominator. This is not a design choice but a mathematical necessity: a cross-comparison is impossible without both values present.

**Deviation threshold and comparison logic:** The relative deviation is computed independently for each of the three dimensions (Länge, Breite, Höhe) as `|grund - werk| / grund`. The maximum of these three per-article deviations is then taken (`max(axis=1)`), and an article is classified as inconsistent if this maximum is strictly greater than 10% (`> 0.10`, not `>= 0.10`). This is configured in `rules.yaml → schwellenwerte.konsistenz_abweichung_max`.

**Division-by-zero handling:** If a Grunddaten dimension value is exactly `0`, the relative deviation for that pair is set to `NaN` (using `np.where`) and that pair is excluded from the max-deviation calculation. This prevents division-by-zero errors and avoids arbitrary classification of zero-dimension records.

**Sanity check:** A boolean `_sanity_check` column is included in the output, verifying that `ausgeschlossen + konsistent + inkonsistent == paare_gesamt`. This is retained for tractability.

---

## 6. Konsistenz Einheit Maße (Unit Consistency KPI)

**Scope:** The task brief asks to check the consistency of dimension units (cm vs. mm). This was interpreted as applying exclusively to length/dimension units, not to quantity units (e.g., g, ml, kg in `Mengeneinheit`).

Regarding which columns could actually be checked: only Werksdaten has an explicit dimension unit column (`Mass_Einheit`), which is therefore the sole target of this KPI. For Grunddaten, the situation is more nuanced. The task brief (page 2) lists `Verpackungseinheit` as a Grunddaten field, but this column is not present in the actual dataset. Instead, Grunddaten contains an undocumented column `Verpackungsart` (e.g., "Flasche, Mehrweg"), which describes packaging type, not a unit of measure. The only unit-related column present in Grunddaten is `Mengeneinheit`, which refers to quantity units (g, ml, kg) rather than physical dimensions, and is therefore out of scope for a dimension unit consistency check.

As a result, the KPI is computed exclusively on `Mass_Einheit` in Werksdaten, with `["cm"]` as the only valid value. No analogous check is possible for Grunddaten given the available data.

**Valid values:** The valid unit is `["cm"]`, defined in `rules.yaml → gueltige_werte.mass_einheit`. Any other value (e.g., `mm (falsch)`) is flagged as invalid.

**Rate denominator:** Both `valid_rate` and `invalid_rate` use `n_gesamt` (total rows) as denominator, consistent with the Vollständigkeit convention.

---

## 7. 1NF Atomicity Check Flagging (Normalization)

**Method:** The check flags any string cell containing one of the configured delimiter characters (`,`, `;`, `/`, `(`, `)`) as a candidate for a 1NF violation. These are candidates only; human judgment is required to confirm whether a flagged value is a genuine violation or a legitimate compound label.

**Scope:** 2NF and 3NF analysis cannot be fully automated and requires domain knowledge. The full case-specific normalization study, including flagged candidate review, functional dependency analysis, and recommendations, is documented and carried out in `diagnostics/normalization_analysis.py` and the accompanying presentation.

**Runtime flag:** The 1NF check is controlled by the boolean flag `normalization.check_1nf` in `config.yaml`. It is disabled by default (`false`) as it is a schema-level, one-time check rather than part of the recurring data quality pipeline.

---

## 8. Preisvalidierung (Price Validation)

**Sentinel values:** The explicit sentinel values `9999.99` and `0.01` are flagged as known placeholder prices (configured in `rules.yaml → preisvalidierung.sentinel_werte`).

**Price range:** Prices outside the range `[0.10, 999.99]` EUR (after sentinel removal) are flagged as out-of-range. The lower bound (`preis_min = 0.10`) is intended to catch near-zero non-sentinel prices. The upper bound (`preis_max = 999.99`) catches implausible outliers. Both thresholds are configured in `rules.yaml → schwellenwerte`.

**Invalid categorization:** Sentinel values, out-of-range prices, and invalid currencies are detected as separate mask categories and combined into a single `mask_invalid`. A price can only be counted once even if it falls into multiple categories (union semantics).

**Valid currencies:** Only `EUR` is listed as a valid currency (`rules.yaml → gueltige_werte.waehrung`). Other currencies found in the data are flagged as invalid. dm-drogerie markt operates in 14 European markets, each with potentially different local currencies. However, since the task brief provides no multi-currency specification, `EUR` is assumed to be the only valid currency for this dataset. Additionally, the specific invalid currencies found in the data can be ruled out on operational grounds: dm does not operate in Switzerland or India, making `CHF` and `INR` invalid regardless of any broader currency policy.

---

## 9. Referenzintegrität (Referential Integrity)

**Referential child-to-parent integrity check:** The check verifies that every `Artikelnummer` in `Kategorisierung` exists in `Grunddaten`. Before comparison, duplicates and null values are removed from `Kategorisierung`, since multiple rows can reference the same article (e.g., multiple category entries per article). The check therefore operates at the level of unique Artikelnummern, not total rows.

Of the unique Artikelnummern found in `Kategorisierung`, 147 are correctly referenced in `Grunddaten` and 176 are not. These 176 are orphan records: Artikelnummern that appear in `Kategorisierung` but have no corresponding entry in the article master data. This is a significant referential integrity issue, as a large portion of the categorization data cannot be linked to any known article.

The orphan rate is computed as `n_orphan / n_unique` (176 / 323 = 54.5%), not over total rows.

---

## 10. Werksdaten Konflikte (Werksdaten Conflicts)

**Two-stage deduplication:** The conflict check explicitly distinguishes:

1. **Exact duplicates**: identical rows across all columns. These are safe to remove.
2. **Conflicts**: rows that share the same composite key `[Artikelnummer, Werk]` but differ in at least one non-key column. Three conflicts were identified: A0068/Werk Nord (differing `Status`: Freigegeben vs. Ausgelistet), A0093/Werk Süd (differing `Lieferant_ID`: 1 vs. 19), and A0391/Werk Ost (differing `Lieferant_ID`: 17 vs. 19). These represent a genuine data quality issue requiring domain knowledge to resolve.

This distinction is important: exact duplicates are a data management failure (e.g., double inserts), while conflicts indicate inconsistent master data across systems or entry points.

**Resolution strategy in Konsistenz KPI:** When Werksdaten contain conflicts, the first occurrence after exact-duplicate removal is used for the dimension consistency comparison. No attempt is made to resolve which conflicting value is 'correct', as this requires domain knowledge. Notably, in all three conflict pairs the dimension columns (`Laenge_cm_werk`, `Breite_cm_werk`, `Hoehe_cm_werk`) are identical, meaning these conflicts do not affect the Konsistenz Maße KPI result.

---

## 11. Plausibilitätscheck Maße (Dimension Plausibility)

**Rule:** A row is classified as implausible if any dimension value (Länge, Breite, Höhe) is `<= 0` (lower bound) or exceeds the threshold defined in `rules.yaml → plausibilitaet_masse.implausibel_max` (upper bound, stored in output column `impl_max_threshold`). Both checks are applied to Grunddaten and Werksdaten dimension columns. The two violation types are reported separately as `impl_min_n` (count of `<= 0` violations) and `impl_max_n` (count of `> impl_max_threshold` violations); a row flagged by either condition counts as one implausible row in `tot_implausibel` (no double-counting).

**Null handling:** Rows with any `NaN` dimension value are first excluded from the implausibility check (reported as `fehlend`). Only non-null rows are evaluated for the `<= 0` and `> impl_max_threshold` conditions.

**Rate denominator:** `tot_implausibel_rate` and `plausibel_rate` use `n_gesamt` (total rows) as denominator.

---

## 12. GTIN / EAN-13 Format Check

**Rule:** GTINs are cast to integer, then to string, and zero-padded to 13 characters via `str.zfill(13)`. The integer conversion removes the `.0` suffix introduced by floating-point storage in Excel. Zero-padding correctly restores single leading zeros that would otherwise be lost after integer conversion. The length is then checked against exactly 13 characters, as required by the EAN-13 standard.

**Check digit validation:** The EAN-13 check digit is not validated; only the digit count is verified. A full check-digit validation would be a more rigorous extension.

**Sentinel GTINs:** Sentinel GTIN values are defined in `rules.yaml` (one sentinel value, `9999999999999`, identified in this dataset for article A0500). Sentinels are excluded from the format check and reported as a separate category, counted toward `tot_invalid` consistently with the price validation check.

**Null handling:** Null GTINs are excluded from all checks and reported separately as `fehlend`. Three articles have a missing GTIN: A0045, A0249, A0440.

---

## 13. Rate Calculation Convention (Summary)

All rates (except `konsistenz_masse`) follow the Microsoft Purview convention:

> `rate = passed / (passed + failed + empty)`  
> Denominator = `n_gesamt` (total rows, including missing values)

A missing value is treated as equally problematic as an invalid value from a data management perspective, as both render the record unusable for downstream processes.

**Exception - Konsistenz Maße:** Uses `n_comparable` as denominator (mathematically required; see Section 5).

---


## 14. Vocabulary Validity Check

**Basic vocabulary validity check:** Controlled vocabulary validation assumptions for `Mengeneinheit`, `Temperaturzone`, `Pfandpflicht` are defined in `rules.yaml`. This check is structurally identical to the mass unit consistency check, as both verify that a column's values belong to a predefined set; the same underlying function `check_konsistenz_einheit_masse` is therefore reused for both, with different configuration passed via `rules.yaml`. This check is disabled by default (`validitaet_vokabular: false` in `config.yaml`) and treated as a diagnostic extra check, as the task brief does not explicitly require controlled vocabulary validation.

**Limitations:** The vocabulary validation check (`run_validitaet_vokabular`) finds values that do not belong to the predefined controlled vocabularies in `rules.yaml`. However, it does not detect semantic misassignments, i.e. cases where a value is formally valid but contextually wrong. The following chapter lists inconsistencies identified through manual inspection that are beyond the scope of the automated checks.

--- 

## 15. Further Observed Data Issues Outside Automated Checks in Grunddaten

The following issues were identified through manual inspection and are not covered by the automated pipeline, either because no formal rule was defined in the task brief or because the check would require cross-field validation beyond the current framework.

**Artikelnummer format:** No automated format validation is performed on Artikelnummer values, as the task brief does not define a format rule. Manual inspection reveals two suspicious entries in Grunddaten: `A99999` (five digits instead of the expected four) and `AAAAA` (no digits, does not follow the apparent `A` + 4-digit pattern). These are likely data entry errors but cannot be flagged automatically without a formally defined format rule. Defining such a rule (e.g., regex `^A\d{4}$`) would be a straightforward extension via `rules.yaml`.

**Warengruppe misassignments:** Three articles are assigned to a clearly wrong Warengruppe: A0285 (Chips Oriental) is listed under Getränke, A0393 (Joghurt mild) under Obst & Gemüse, and A0400 (Reisnudeln) under Fleisch & Wurst. These are plausible data entry errors that the current automated vocabulary check cannot detect, as the assigned values are themselves valid Warengruppe entries.

**Warengruppe vs. Temperaturzone mismatches:** Several articles show an implausible combination of Warengruppe and Temperaturzone. A0014 (Limonade, Getränke) is assigned Tiefkühl, which is implausible for a standard beverage. Three Tiefkühlkost articles (A0089 Pommes TK gewellt, A0373 Pizza TK, A0473 Pommes TK geschnitten) are assigned Kühl or have a missing Temperaturzone, whereas Tiefkühlkost by definition requires Tiefkühl. Additionally, 14 Molkereiprodukte articles are assigned Ambient, whereas dairy products are normally stored under Kühl conditions.

**Mengeneinheit semantically wrong for category:** Several Obst & Gemüse articles have Mengeneinheit = ml (e.g., Kartoffel, Banane), which is semantically incorrect, as fresh produce is typically measured in g or as whole units, not millilitres.

**Pfandpflicht = Ja on non-beverage articles:** In the German market, Pfand applies primarily to beverage containers and certain glass packaging (e.g., yogurt jars). However, a number of articles for which a deposit is difficult to justify were found carrying Pfandpflicht = Ja, including Kartoffel Bio (A0004), Karotte Bio (A0068), Keks Bio (A0077), Croissant (A0082), and Olivenöl (A0403), among others.

**Scope note:** These findings are documented here as known limitations of the automated pipeline. Detecting semantic misassignments at scale would require **cross-field rule validation** (e.g., if Warengruppe = Tiefkühlkost then Temperaturzone must = Tiefkühl) or enrichment with external reference data. Both are feasible extensions to the current framework via `rules.yaml`.
