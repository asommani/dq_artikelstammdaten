"""
dashboard.py -- Aufgabe 3: Visualisierung der Datenqualitaet.

Erzeugt ein interaktives Plotly-Dashboard mit 5 Panels:
    Panel 1 -- KPI Scorecard (Vollstaendigkeit, Eindeutigkeit, Konsistenz Masse)
    Panel 2 -- Preisvalidierung (Sentinel, Waehrung, Valid)
    Panel 3 -- Masse Konsistenz (Grunddaten vs. Werksdaten + Einheitenfehler)
    Panel 4 -- Kategorisierung Referenzintegritaet (Phantom Records)
    Panel 5 -- Vollstaendigkeit per Pflichtfeld

Output:  output/<run>/dashboard/dashboard.html  +  dashboard.png
"""

import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from .utils import get_output_dir

# ── Design ────────────────────────────────────────────────────
DM_ROT  = "#CC0033"
GRUEN   = "#27AE60"   # kept for non-KPI charts (bars, donuts)
GELB    = "#E67E22"
ROT     = "#E74C3C"
GRAU_BG = "#F4F6F7"
GRAU_LN = "#D5D8DC"
GRAU_TX = "#95A5A6"
DUNKEL  = "#2C3E50"
WEISS   = "#FFFFFF"
FONT    = "Arial, Helvetica, sans-serif"

# 5-level KPI traffic-light (fixed thresholds, applies to all gauges)
C100 = "#1A9850"   # 100 %         dark green
C98  = "#91CF60"   # [98 – 100) %  light green
C95  = "#f7c434"   # [95 –  98) %  yellow
C90  = "#FC8D59"   # [90 –  95) %  orange
CRED = "#D73027"   # < 90 %        red

# lighter zone fills for gauge background steps
_STEP_COLORS = [
    (  0,  90, "#F9D5D3"),   # red zone
    ( 90,  95, "#FDE8D5"),   # orange zone
    ( 95,  98, "#FFFDE5"),   # yellow zone
    ( 98, 100, "#EBF7E8"),   # light-green zone
]


def _farbe(v: float) -> str:
    """5-level traffic-light colour for a rate in [0, 1]."""
    if v >= 1.00: return C100
    if v >= 0.98: return C98
    if v >= 0.95: return C95
    if v >= 0.90: return C90
    return CRED


# ── Panel 1: Gauges (5 KPIs) ─────────────────────────────────

def _panel1_gauges(fig, vollst, artik, gtin, kons, einh):
    kpis = [
        ("Vollständigkeit",       "Pflichtfelder · Grunddaten",  vollst, 1),
        ("Eindeutigkeit",         "Artikelnummer",               artik,  2),
        ("Eindeutigkeit",         "GTIN (EAN-13)",               gtin,   3),
        ("Konsistenz Maße",       "Grunddaten vs. Werksdaten",   kons,   4),
        ("Konsistenz Maßeinheit", "Mass_Einheit Werksdaten",     einh,   5),
    ]
    for title, sub, wert, col in kpis:
        farbe = _farbe(wert)
        fig.add_trace(go.Indicator(
            mode  = "gauge+number",
            value = round(wert * 100, 1),
            number = dict(suffix=" %", font=dict(size=24, color=farbe, family=FONT)),
            title  = dict(
                text = f"<b>{title}</b><br><span style='font-size:9px;color:{GRAU_TX}'>{sub}</span>",
                font = dict(size=11, family=FONT, color=DUNKEL),
            ),
            gauge = dict(
                axis  = dict(range=[0, 100], ticksuffix="%",
                             tickfont=dict(size=7, color=GRAU_TX),
                             nticks=6),
                bar   = dict(color=farbe, thickness=0.22),
                bgcolor = GRAU_BG,
                borderwidth = 0,
                threshold = dict(line=dict(color=DUNKEL, width=2),
                                 thickness=0.75, value=98),   # 98% target line
                steps = [dict(range=[lo, hi], color=c)
                         for lo, hi, c in _STEP_COLORS],
            ),
        ), row=1, col=col)


# ── Panel 2: Preisvalidierung ─────────────────────────────────

def _panel2_preis(fig, sentinel, waehrung, valid, gesamt, invalid):
    # invalid = union(sentinel OR wrong_currency) -- groups overlap, do NOT stack them separately
    # correct breakdown: valid(41) + invalid(117) = 158
    segs = [
        (valid,   GRUEN, f"✓ Gültig: {valid} ({valid/gesamt*100:.0f}%)"),
        (invalid, ROT,   f"✕ Ungültig: {invalid} ({invalid/gesamt*100:.0f}%)"),
    ]
    cat = [f"{gesamt} Preiseinträge"]
    for wert, farbe, label in segs:
        hover_detail = (
            f"  davon Sentinel-Platzhalter: {sentinel}<br>"
            f"  davon Falsche Währung (CHF/INR): {waehrung}<br>"
            f"  (Gruppen können sich überschneiden)"
            if wert == invalid else ""
        )
        fig.add_trace(go.Bar(
            name        = label,
            x           = [wert],
            y           = cat,
            orientation = "h",
            marker_color = farbe,
            text        = [f"<b>{wert}</b>  ({wert/gesamt*100:.0f}%)"],
            textposition = "inside",
            insidetextanchor = "middle",
            textfont    = dict(color=WEISS, size=12, family=FONT),
            hovertemplate = f"<b>{label}</b><br>{hover_detail}<extra></extra>",
            showlegend  = True,
            width       = 0.55,
        ), row=2, col=1)


# ── Panel 3: Maße – zwei gestapelte Balken ────────────────────

def _panel3_masse(fig, konsistent, inkonsistent, einheit_ok, einheit_bug):
    n_kons = konsistent + inkonsistent
    n_einh = einheit_ok + einheit_bug

    pairs = [
        # (cat_label, ok_val, bad_val, ok_color, bad_color, ok_hover, bad_hover)
        (
            "Konsistenz<br>Grund↔Werk",
            konsistent, inkonsistent,
            GRUEN, ROT,
            f"Konsistent: {konsistent} ({konsistent/n_kons*100:.0f}%)",
            f"Inkonsistent (>10 %): {inkonsistent} ({inkonsistent/n_kons*100:.0f}%)",
        ),
        (
            "Maßeinheit<br>Werksdaten",
            einheit_ok, einheit_bug,
            GRUEN, GELB,
            f"Korrekt (cm): {einheit_ok} ({einheit_ok/n_einh*100:.0f}%)",
            f"Fehler 'mm (falsch)': {einheit_bug} ({einheit_bug/n_einh*100:.0f}%)",
        ),
    ]

    first = True
    for cat, ok_v, bad_v, ok_c, bad_c, ok_h, bad_h in pairs:
        total = ok_v + bad_v
        fig.add_trace(go.Bar(
            name         = ok_h,
            x            = [cat],
            y            = [ok_v],
            marker_color = ok_c,
            text         = [f"<b>{ok_v}</b><br>({ok_v/total*100:.0f}%)"],
            textposition = "inside",
            insidetextanchor = "middle",
            textfont     = dict(color=WEISS, size=10, family=FONT),
            hovertemplate = f"<b>{ok_h}</b><extra></extra>",
            showlegend   = False,
        ), row=2, col=4)
        fig.add_trace(go.Bar(
            name         = bad_h,
            x            = [cat],
            y            = [bad_v],
            marker_color = bad_c,
            text         = [f"<b>{bad_v}</b><br>({bad_v/total*100:.0f}%)"],
            textposition = "inside",
            insidetextanchor = "middle",
            textfont     = dict(color=WEISS, size=10, family=FONT),
            hovertemplate = f"<b>{bad_h}</b><extra></extra>",
            showlegend   = False,
        ), row=2, col=4)


# ── Panel 4: Referenzintegrität Donut ─────────────────────────

def _panel4_ref(fig, ref, verwaist):
    total = ref + verwaist
    fig.add_trace(go.Pie(
        labels   = [f"Referenziert ({ref})", f"Phantom-Records ({verwaist})"],
        values   = [ref, verwaist],
        hole     = 0.60,
        marker   = dict(colors=[GRUEN, ROT], line=dict(color=WEISS, width=2)),
        textinfo = "label+percent",
        textfont = dict(size=10, family=FONT),
        hovertemplate = "<b>%{label}</b><br>Anteil: %{percent}<extra></extra>",
        showlegend = False,
    ), row=3, col=1)


# ── Panel 5: Vollständigkeit per Feld ─────────────────────────

def _panel5_vollst(fig, df_voll):
    df = df_voll[df_voll["feld"] != "_gesamt"].sort_values("vollstaendigkeit")
    farben = [_farbe(v) for v in df["vollstaendigkeit"]]
    fig.add_trace(go.Bar(
        x            = df["vollstaendigkeit"] * 100,
        y            = df["feld"],
        orientation  = "h",
        marker_color = farben,
        text         = [f"{v*100:.1f}%" for v in df["vollstaendigkeit"]],
        textposition = "outside",
        cliponaxis   = False,
        textfont     = dict(size=9, color=DUNKEL, family=FONT),
        hovertemplate = "<b>%{y}</b>: %{x:.1f}%<extra></extra>",
        showlegend   = False,
    ), row=3, col=3)


# ── Hauptfunktion ─────────────────────────────────────────────

def build_dashboard(
    vollstaendigkeit_results,
    eindeutigkeit_results,
    konsistenz_masse_result,
    konsistenz_einheit_result,
    preisvalidierung_result,
    referenzintegritaet_results,
    werksdaten_konflikte_result,
) -> go.Figure:

    # Extract values
    df_voll  = vollstaendigkeit_results["artikeldaten_grunddaten"]
    df_eind  = eindeutigkeit_results["artikeldaten_grunddaten"]

    vollst     = float(df_voll[df_voll["feld"] == "_gesamt"]["vollstaendigkeit"].iloc[0])
    artik_rate = float(df_eind[df_eind["feld"] == "Artikelnummer"]["eindeutig_rate"].iloc[0])
    gtin       = float(df_eind[df_eind["feld"] == "GTIN"]["eindeutig_rate"].iloc[0])
    kons       = float(konsistenz_masse_result["konsistent_rate"].iloc[0])
    einh_rate  = float(konsistenz_einheit_result["valid_rate"].iloc[0])
    kon_n  = int(konsistenz_masse_result["konsistent"].iloc[0])
    ink_n  = int(konsistenz_masse_result["inkonsistent"].iloc[0])
    einh_ok  = int(konsistenz_einheit_result["valid"].iloc[0])
    einh_bug = int(konsistenz_einheit_result["invalid"].iloc[0])
    sentinel  = int(preisvalidierung_result["sentinel"].iloc[0])
    invalid_p = int(preisvalidierung_result["invalid_gesamt"].iloc[0])
    waehrung = int(preisvalidierung_result["ungueltige_waehrung"].iloc[0])
    valid_p  = int(preisvalidierung_result["valid"].iloc[0])
    gesamt_p = int(preisvalidierung_result["gesamt"].iloc[0])
    df_ref   = referenzintegritaet_results["kategorisierung"]
    ref_n    = int(df_ref["referenziert"].iloc[0])
    ver_n    = int(df_ref["verwaist"].iloc[0])
    wk_konf  = int(werksdaten_konflikte_result["konflikte"].iloc[0])

    # ── Subplots ──────────────────────────────────────────────
    specs = [
        # Row 1: 5 KPI gauges
        [{"type": "indicator"}] * 5,
        # Row 2: Panel 2 (colspan=3, left) | Panel 3 (colspan=2, right)
        [{"type": "xy", "colspan": 3}, None, None, {"type": "xy", "colspan": 2}, None],
        # Row 3: Panel 4 (domain, colspan=2, left) | Panel 5 (xy, colspan=3, right)
        [{"type": "domain", "colspan": 2}, None, {"type": "xy", "colspan": 3}, None, None],
    ]

    fig = make_subplots(
        rows=3, cols=5,
        specs=specs,
        row_heights        = [0.28, 0.36, 0.36],
        vertical_spacing   = 0.14,
        horizontal_spacing = 0.05,
    )

    _panel1_gauges(fig, vollst, artik_rate, gtin, kons, einh_rate)
    _panel2_preis(fig,  sentinel, waehrung, valid_p, gesamt_p, invalid_p)
    _panel3_masse(fig,  kon_n, ink_n, einh_ok, einh_bug)
    _panel4_ref(fig,    ref_n, ver_n)
    _panel5_vollst(fig, df_voll)

    # ── Achsen ────────────────────────────────────────────────
    # Panel 2: hide x-axis ticks, keep y-axis clean
    fig.update_xaxes(showgrid=False, showticklabels=False, row=2, col=1)
    fig.update_yaxes(showgrid=False, tickfont=dict(size=11), row=2, col=1)

    # Panel 3: vertical grouped bars
    fig.update_xaxes(showgrid=False, tickfont=dict(size=10), row=2, col=4)
    fig.update_yaxes(showgrid=True, gridcolor=GRAU_LN, row=2, col=4)

    # Panel 5: horizontal bars
    fig.update_xaxes(range=[87, 103], showgrid=True, gridcolor=GRAU_LN,
                     ticksuffix="%", tickfont=dict(size=9), row=3, col=3)
    fig.update_yaxes(tickfont=dict(size=9), showgrid=False, row=3, col=3)

    # 100% reference line Panel 5
    fig.add_shape(type="line",
        x0=100, x1=100, y0=0, y1=1,
        xref="x3", yref="y3 domain",
        line=dict(color=GRAU_TX, dash="dot", width=1))

    # ── Panel headers (manual annotations, no subplot_titles clash) ─
    # y coords derived from row_heights=[0.26,0.37,0.37], v_spacing=0.14:
    #   content_height = 1 - 2*0.14 = 0.72
    #   row3 bottom: y=0           top: y = 0.37*0.72 = 0.266
    #   row2 bottom: y=0.266+0.14  top: y = 0.406 + 0.37*0.72 = 0.672
    #   row1 bottom: y=0.672+0.14  top: y = 0.812 + 0.26*0.72 = 1.000
    # header y = just above top of each row

    HEADER_Y_ROW1 = 1.035   # above gauge row (inside top margin)
    HEADER_Y_ROW2 = 0.692
    HEADER_Y_ROW3 = 0.285

    # x starts: with h_spacing=0.08, col_width=(1-2*0.08)/3=0.28
    #   col1 x0=0,     col2 x0=0.36,  col3 x0=0.72
    HEADER_X_COL1 = 0.01
    HEADER_X_COL3 = 0.64   # Panel 3: col4 of 5-col grid

    # Row 3: Panel 5 starts at col2 x0 ≈ 0.36
    HEADER_X_P5   = 0.43   # Panel 5: col3 of 5-col grid

    headers = [
        (HEADER_X_COL1, HEADER_Y_ROW1, "① KPI-Scorecard — Kernindikatoren"),
        (HEADER_X_COL1, HEADER_Y_ROW2, "② Preisvalidierung  →  Kundenservice & Legal"),
        (HEADER_X_COL3, HEADER_Y_ROW2, "③ Maße-Konsistenz  →  Logistik"),
        (HEADER_X_COL1, HEADER_Y_ROW3, "④ Referenzintegrität Kategorisierung  →  Marketing"),
        (HEADER_X_P5,   HEADER_Y_ROW3, "⑤ Vollständigkeit Pflichtfelder  →  Alle Bereiche"),
    ]

    annotations = []
    for x, y, text in headers:
        annotations.append(dict(
            x=x, y=y, xref="paper", yref="paper",
            text=f"<b>{text}</b>",
            font=dict(size=11, color=DUNKEL, family=FONT),
            showarrow=False, xanchor="left",
        ))

    # Donut centre label for Panel 4
    annotations.append(dict(
        x=0.185, y=0.133,
        xref="paper", yref="paper",
        text=f"<b style='font-size:15px;color:{ROT}'>{ver_n/( ref_n+ver_n)*100:.0f}%</b>"
             f"<br><span style='font-size:9px;color:{GRAU_TX}'>Phantome</span>",
        showarrow=False, align="center",
    ))


    # Horizontal dividers between rows
    dividers = [
        dict(type="line", x0=0, x1=1, y0=0.293, y1=0.293,
             xref="paper", yref="paper", line=dict(color=GRAU_LN, width=1)),
        dict(type="line", x0=0, x1=1, y0=0.699, y1=0.699,
             xref="paper", yref="paper", line=dict(color=GRAU_LN, width=1)),
    ]

    # ── Global layout ─────────────────────────────────────────
    fig.update_layout(
        title=dict(
            text=(
                f"<b>Datenqualität Artikelstammdaten</b>"
                # f"<br><span style='font-size:12px;color:{GRAU_TX}'>"
                # f"dm-drogerie markt · Recruiting Data Analyst · "
                # f"Anna Sommani · 13. April 2026</span>"
            ),
            x=0.01, xanchor="left",
            font=dict(size=19, color=DM_ROT, family=FONT),
        ),
        paper_bgcolor = WEISS,
        plot_bgcolor  = WEISS,
        font          = dict(family=FONT, color=DUNKEL),
        height        = 1020,
        margin        = dict(t=105, b=90, l=20, r=20),
        barmode       = "stack",
        bargap        = 0.25,
        annotations   = annotations,
        shapes        = dividers,
        legend        = dict(
            orientation = "h",
            x=0.01, y=-0.06,
            xanchor="left", yanchor="top",
            font=dict(size=10, family=FONT),
            bgcolor="rgba(0,0,0,0)",
            title=dict(text="② Legende Preisvalidierung  ", font=dict(size=10, color=GRAU_TX)),
        ),
    )

    return fig


def run_dashboard(
    vollstaendigkeit_results,
    eindeutigkeit_results,
    konsistenz_masse_result,
    konsistenz_einheit_result,
    preisvalidierung_result,
    referenzintegritaet_results,
    werksdaten_konflikte_result,
    config,
    run_dir,
) -> None:
    """Erzeugt Dashboard und speichert in output/<run>/dashboard/."""
    output_dir = get_output_dir(run_dir, "dashboard")

    fig = build_dashboard(
        vollstaendigkeit_results    = vollstaendigkeit_results,
        eindeutigkeit_results       = eindeutigkeit_results,
        konsistenz_masse_result     = konsistenz_masse_result,
        konsistenz_einheit_result   = konsistenz_einheit_result,
        preisvalidierung_result     = preisvalidierung_result,
        referenzintegritaet_results = referenzintegritaet_results,
        werksdaten_konflikte_result = werksdaten_konflikte_result,
    )

    html_path = os.path.join(output_dir, "dashboard.html")
    fig.write_html(html_path, include_plotlyjs="cdn")
    print(f"  Gespeichert: {os.path.basename(html_path)}")

    try:
        png_path = os.path.join(output_dir, "dashboard.png")
        fig.write_image(png_path, width=1600, height=1020, scale=2)
        print(f"  Gespeichert: {os.path.basename(png_path)}")
    except Exception as e:
        print(f"  PNG-Export fehlgeschlagen (kaleido + Chrome benoetigt): {e}")
        print("  Tipp: plotly_get_chrome")
