"""
DASHBOARD — HotelPulse MVP (visual estilo "produto")

A sidebar foi simplificada por pedido: só logo + item único
"Relatórios" + seletor de hotel. Todo o conteúdo (métricas,
gráficos, recomendações) fica nesta única tela.

Rodar com:
    streamlit run dashboard/app.py
"""

import sys
import os
from datetime import date

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import run_query
from engine.revenue_engine import (
    load_hotel_data,
    load_competitor_data,
    compute_dashboard_summary,
    compute_competitive_position,
    get_top_opportunity_message,
)

st.set_page_config(page_title="HotelPulse", page_icon="🏨", layout="wide")

# ---- Carrega CSS customizado ----
CSS_PATH = os.path.join(os.path.dirname(__file__), "styles.css")
with open(CSS_PATH, "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def html(content: str):
    """
    Renderiza HTML customizado via st.markdown, "achatando" a string
    antes de enviar.

    Por quê: quando montamos HTML com f-strings multi-linha indentadas
    (comum ao concatenar linhas de tabela em um loop), o Markdown do
    Streamlit interpreta blocos com 4+ espaços de indentação, precedidos
    de uma linha em branco, como CÓDIGO — e mostra a tag <tr> crua na
    tela em vez de renderizar. Achatar tudo em uma linha só elimina
    esse problema de vez, para qualquer HTML que passarmos por aqui.
    Use esta função (não st.markdown) sempre que injetar HTML/CSS.
    """
    flat = " ".join(line.strip() for line in content.strip().splitlines() if line.strip())
    st.markdown(flat, unsafe_allow_html=True)


# =========================================================
# SIDEBAR — logo + item único "Relatórios" + seletor de hotel
# =========================================================
hotels = run_query("SELECT id, name, city FROM hotels ORDER BY name")

with st.sidebar:
    html("""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
            <span style="font-size:1.6rem;">📶</span>
            <div>
                <div class="hp-logo-title">HotelPulse</div>
                <div class="hp-logo-tagline">Mais receita. Mais ocupação.</div>
            </div>
        </div>
    """)

    html("""<div class="hp-nav-item">📄&nbsp;&nbsp;Relatórios</div>""")

    if not hotels:
        st.warning("Nenhum hotel cadastrado. Rode `python main.py` primeiro.")
        st.stop()

    hotel_options = {f"{h['name']}": h["id"] for h in hotels}
    html("<div style='margin-top:2rem;'></div>")
    selected_label = st.selectbox("Hotel", list(hotel_options.keys()), label_visibility="collapsed")
    hotel_id = hotel_options[selected_label]
    hotel_city = [h["city"] for h in hotels if h["id"] == hotel_id][0]

    html(f"""
        <div class="hp-hotel-card">
            <span style="font-size:1.3rem;">🏨</span>
            <div>
                <div class="hp-hotel-name">{selected_label}</div>
                <div class="hp-hotel-city">{hotel_city}</div>
            </div>
        </div>
    """)


# =========================================================
# CARREGA DADOS
# =========================================================
summary = compute_dashboard_summary(hotel_id)
daily = load_hotel_data(hotel_id)
comp_df = load_competitor_data(hotel_id)
recs = pd.DataFrame(run_query(
    "SELECT * FROM recommendations WHERE hotel_id = :hid ORDER BY date",
    {"hid": hotel_id},
))
events = run_query(
    "SELECT * FROM demand_events WHERE city = :city AND date >= :today ORDER BY date LIMIT 6",
    {"city": hotel_city, "today": date.today().isoformat()},
)

if daily.empty:
    st.info("Sem dados para este hotel ainda. Rode `python main.py`.")
    st.stop()

daily["revpar"] = daily["adr"] * daily["occupancy_pct"] / 100


def fmt_delta(value):
    sign = "↑" if value >= 0 else "↓"
    cls = "positive" if value >= 0 else "negative"
    return f'<span class="hp-metric-delta {cls}">{sign} {abs(value):.0f}%</span>'


# =========================================================
# CABEÇALHO
# =========================================================
col_title, col_date = st.columns([3, 1])
with col_title:
    st.markdown("### Olá! 👋")
    st.caption("Aqui está o resumo da performance do seu hotel e as principais oportunidades para aumentar sua receita.")
with col_date:
    html(f"""<div style="text-align:right; padding-top:1.2rem; color:#64748b;">
        📅 {daily['date'].iloc[-1]}</div>""")

# =========================================================
# CARDS DE MÉTRICA
# =========================================================
c1, c2, c3, c4 = st.columns(4)

metric_cards = [
    (c1, "🛏️", "Ocupação", f"{summary['occupancy_avg']:.0f}%", summary["occupancy_delta"],
     "vs. período anterior", "var(--hp-green-bg)", "var(--hp-green)", min(summary["occupancy_avg"], 100)),
    (c2, "🗄️", "ADR (Diária Média)", f"R$ {summary['adr_avg']:.0f}", summary["adr_delta"],
     "vs. período anterior", "var(--hp-blue-bg)", "var(--hp-blue)", min(summary["adr_avg"] / 4, 100)),
    (c3, "📊", "RevPAR", f"R$ {summary['revpar_avg']:.0f}", summary["revpar_delta"],
     "vs. período anterior", "var(--hp-purple-bg)", "var(--hp-purple)", min(summary["revpar_avg"] / 3, 100)),
    (c4, "🛌", "Quartos Disponíveis", f"{summary['rooms_available_latest']}",
     None, f"de {summary['total_rooms']}", "var(--hp-orange-bg)", "var(--hp-orange)",
     (summary["rooms_available_latest"] / summary["total_rooms"]) * 100),
]

for col, icon, label, value, delta, sub, icon_bg, bar_color, progress in metric_cards:
    delta_html = fmt_delta(delta) if delta is not None else ""
    with col:
        html(f"""
            <div class="hp-metric-card">
                <div class="hp-metric-header">
                    <span class="hp-metric-icon" style="background:{icon_bg};">{icon}</span>
                    {label}
                </div>
                <div>
                    <span class="hp-metric-value">{value}</span>{delta_html}
                </div>
                <div class="hp-metric-sub">{sub}</div>
                <div class="hp-progress-track">
                    <div class="hp-progress-fill" style="width:{progress:.0f}%; background:{bar_color};"></div>
                </div>
            </div>
        """)

html("<div style='margin-top:1.2rem;'></div>")

# =========================================================
# EVOLUÇÃO + POSIÇÃO COMPETITIVA + RECOMENDAÇÃO DO DIA
# =========================================================
col_chart, col_pos, col_reco = st.columns([1.6, 1.2, 1.2])

with col_chart:
    html("""<div class="hp-panel"><div class="hp-panel-title">Evolução da Ocupação, ADR e RevPAR</div>
        <div class="hp-panel-subtitle">Últimos dias disponíveis</div>""")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily["date"], y=daily["occupancy_pct"], name="Ocupação (%)",
                              line=dict(color="#10b981", width=2), yaxis="y1"))
    fig.add_trace(go.Scatter(x=daily["date"], y=daily["adr"], name="ADR (R$)",
                              line=dict(color="#3b82f6", width=2), yaxis="y2"))
    fig.add_trace(go.Scatter(x=daily["date"], y=daily["revpar"], name="RevPAR (R$)",
                              line=dict(color="#8b5cf6", width=2), yaxis="y2"))
    fig.update_layout(
        height=320, margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        yaxis=dict(title="Ocupação (%)", range=[0, 100]),
        yaxis2=dict(title="R$", overlaying="y", side="right"),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    html("</div>")

with col_pos:
    pos_df = compute_competitive_position(hotel_id)
    html("""<div class="hp-panel"><div class="hp-panel-title">Posição Competitiva</div>
        <div class="hp-panel-subtitle">Sua tarifa vs. concorrentes (última data)</div>""")
    if pos_df.empty:
        st.caption("Sem dados de concorrência suficientes ainda.")
    else:
        rows_html = ""
        colors = ["#10b981", "#3b82f6", "#f97316", "#ef4444", "#a855f7", "#f43f5e", "#64748b"]
        for i, r in pos_df.iterrows():
            color = "#0f172a" if r["is_own"] else colors[i % len(colors)]
            diff_color = "#047857" if r["diff_pct"] >= 0 else "#b91c1c"
            diff_sign = "+" if r["diff_pct"] >= 0 else ""
            rows_html += (
                f'<tr><td><span class="hp-dot" style="background:{color};"></span>{r["hotel"]}</td>'
                f'<td>R$ {r["rate"]:.0f}</td>'
                f'<td style="color:{diff_color}; font-weight:600;">{diff_sign}{r["diff_pct"]:.0f}%</td></tr>'
            )
        html(
            f'<table class="hp-table">'
            f'<tr><th>Hotel</th><th>Tarifa</th><th>Diferença</th></tr>'
            f'{rows_html}</table>'
        )
    html("</div>")

with col_reco:
    top_rec = recs[recs["action"] == "aumentar"].head(1)
    html('<div class="hp-reco-card">')
    html(
        '<div class="hp-panel-title">💡 Recomendação do Dia '
        '<span class="hp-badge aumentar" style="margin-left:6px;">Oportunidade</span></div>'
    )
    if top_rec.empty:
        html('<div class="hp-checklist-item">Nenhuma oportunidade de aumento no momento.</div>')
    else:
        r = top_rec.iloc[0]
        html(f'<div class="hp-checklist-item">{r["date"]}</div>')
        html(f"""
            <div class="hp-reco-highlight">
                <div class="label">↑ Aumentar tarifa para</div>
                <div class="value">R$ {r['suggested_rate_min']:.0f} – {r['suggested_rate_max']:.0f}</div>
            </div>
            <div class="hp-checklist-item">Por quê?</div>
            <div class="hp-checklist-item">✅ Ocupação atual em {r['occupancy_pct']:.0f}%</div>
            <div class="hp-checklist-item">✅ Tarifa atual abaixo da média dos concorrentes</div>
            <div class="hp-checklist-item">✅ Demanda prevista: {r['demand_level']}</div>
        """)
    html("</div>")

html("<div style='margin-top:1.2rem;'></div>")

# =========================================================
# DEMANDA E EVENTOS + DESEMPENHO + COMPARATIVO DE TARIFAS
# =========================================================
col_events, col_perf, col_bar = st.columns([1.3, 1, 1.3])

with col_events:
    html("""<div class="hp-panel"><div class="hp-panel-title">📅 Demanda e Eventos</div>
        <div class="hp-panel-subtitle">Próximos dias de alta demanda</div>""")
    if not events:
        st.caption("Nenhum evento cadastrado ainda.")
    else:
        for e in events:
            badge_class = e["demand_impact"]
            html(f"""
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                    <span style="font-size:0.8rem; color:#64748b; width:60px;">{e['date'][5:]}</span>
                    <span class="hp-badge {badge_class}">{e['demand_impact'].capitalize()}</span>
                    <span style="font-size:0.85rem;">{e['name']}</span>
                </div>
            """)
    html("</div>")

with col_perf:
    html("""<div class="hp-panel"><div class="hp-panel-title">📈 Seu Desempenho</div>
        <div class="hp-panel-subtitle">Período disponível</div>""")
    revenue_fmt = f"{summary['revenue_total']:,.0f}".replace(",", ".")
    html(f"""
        <div style="margin-bottom:14px;">
            <div class="hp-metric-sub">Receita Total</div>
            <div class="hp-metric-value" style="font-size:1.3rem;">R$ {revenue_fmt}</div>
        </div>
        <div style="margin-bottom:14px;">
            <div class="hp-metric-sub">Diárias Vendidas</div>
            <div class="hp-metric-value" style="font-size:1.3rem;">{summary['rooms_sold_total']}</div>
        </div>
        <div style="margin-bottom:14px;">
            <div class="hp-metric-sub">Ocupação Média</div>
            <div class="hp-metric-value" style="font-size:1.3rem;">{summary['occupancy_month_avg']:.0f}%</div>
        </div>
        <div>
            <div class="hp-metric-sub">Diária Média (ADR)</div>
            <div class="hp-metric-value" style="font-size:1.3rem;">R$ {summary['adr_month_avg']:.0f}</div>
        </div>
    """)
    html("</div>")

with col_bar:
    html("""<div class="hp-panel"><div class="hp-panel-title">📊 Comparativo de Tarifas</div>
        <div class="hp-panel-subtitle">Última data disponível</div>""")
    if pos_df.empty:
        st.caption("Sem dados de concorrência suficientes ainda.")
    else:
        bar_colors = ["#0f172a" if own else "#cbd5e1" for own in pos_df["is_own"]]
        fig_bar = go.Figure(go.Bar(
            x=pos_df["hotel"].str.replace(r"Seu hotel \(.*\)", "Seu hotel", regex=True),
            y=pos_df["rate"], marker_color=bar_colors,
            text=pos_df["rate"].apply(lambda v: f"R$ {v:.0f}"), textposition="outside",
        ))
        fig_bar.update_layout(
            height=280, margin=dict(l=10, r=10, t=20, b=10),
            plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
    html("</div>")

html("<div style='margin-top:1.2rem;'></div>")

# =========================================================
# TABELA DE RECOMENDAÇÕES + QUOTE
# =========================================================
col_table, col_quote = st.columns([2, 1])

with col_table:
    html("""<div class="hp-panel"><div class="hp-panel-title">🧾 Recomendações de Tarifas</div>
        <div class="hp-panel-subtitle">Sugestões para os próximos dias</div>""")
    if recs.empty:
        st.caption("Nenhuma recomendação gerada ainda. Rode `python engine/revenue_engine.py`.")
    else:
        rows_html = ""
        for _, r in recs.sort_values("date").head(7).iterrows():
            badge = r["action"]
            rows_html += (
                f'<tr><td>{r["date"]}</td>'
                f'<td>{r["occupancy_pct"]:.0f}%</td>'
                f'<td>R$ {r["current_rate"]:.0f}</td>'
                f'<td>R$ {r["suggested_rate_min"]:.0f} – {r["suggested_rate_max"]:.0f}</td>'
                f'<td><span class="hp-badge {badge}">{badge.capitalize()}</span></td></tr>'
            )
        html(
            f'<table class="hp-table">'
            f'<tr><th>Data</th><th>Ocupação</th><th>Tarifa Atual</th><th>Tarifa Sugerida</th><th>Ação</th></tr>'
            f'{rows_html}</table>'
        )
    html("</div>")

with col_quote:
    quote = get_top_opportunity_message(hotel_id)
    html(f"""
        <div class="hp-quote-card">
            <div style="font-size:1.5rem;">🔔</div>
            <div class="hp-quote-text">"{quote}"</div>
            <div style="margin-top:14px; font-size:0.8rem; color:#64748b; font-weight:600;">HotelPulse</div>
            <div style="font-size:0.75rem; color:#94a3b8;">Inteligência de Revenue Management</div>
        </div>
    """)