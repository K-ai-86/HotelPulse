"""
Tela de cadastro de dados: hotel, concorrência, eventos e grupos.
"""

import streamlit as st
from datetime import date

from ingestion.hotel_data import import_daily_data
from ingestion.competitor_data import add_competitor, import_rate
from ingestion.ingestion_events_data import add_event
from ingestion.ingestion_groups_data import add_group_booking


def render_cadastro(hotel_id: int, hotel_city: str):
    st.markdown("### 📝 Cadastro de dados")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Dados do hotel", "Concorrência", "Eventos/Feriados", "Grupos"]
    )

    # ---- ABA 1: Dados diários do hotel ----
    with tab1:
        with st.form("form_hotel_data"):
            col1, col2 = st.columns(2)
            data = col1.date_input("Data", value=date.today())
            ocupacao = col2.number_input("Ocupação (%)", min_value=0.0, max_value=100.0, step=1.0)
            col3, col4 = st.columns(2)
            adr = col3.number_input("ADR / Diária média (R$)", min_value=0.0, step=1.0)
            quartos_disp = col4.number_input("Quartos disponíveis", min_value=0, step=1)
            reservas_7d = st.number_input("Reservas para os próximos 7 dias", min_value=0, step=1)

            if st.form_submit_button("Salvar dados do hotel"):
                import_daily_data(
                    hotel_id=hotel_id, date=str(data), occupancy_pct=ocupacao,
                    adr=adr, rooms_available=int(quartos_disp),
                    reservations_next_7d=int(reservas_7d),
                )
                st.success(f"Dados de {data} salvos com sucesso!")

    # ---- ABA 2: Tarifas de concorrentes ----
    with tab2:
        with st.form("form_competitor"):
            nome_concorrente = st.text_input("Nome do concorrente")
            col1, col2 = st.columns(2)
            data_comp = col1.date_input("Data", value=date.today(), key="data_comp")
            tarifa = col2.number_input("Tarifa (R$)", min_value=0.0, step=1.0)

            if st.form_submit_button("Salvar tarifa do concorrente"):
                competitor_id = add_competitor(hotel_id, nome_concorrente)
                import_rate(competitor_id, str(data_comp), tarifa)
                st.success(f"Tarifa de {nome_concorrente} salva!")

    # ---- ABA 3: Eventos e feriados ----
    with tab3:
        with st.form("form_event"):
            nome_evento = st.text_input("Nome do evento/feriado")
            data_evento = st.date_input("Data", value=date.today(), key="data_evento")
            impacto = st.selectbox("Impacto na demanda", ["baixo", "medio", "alto"])

            if st.form_submit_button("Salvar evento"):
                add_event(hotel_city, str(data_evento), nome_evento, impacto)
                st.success(f"Evento '{nome_evento}' salvo!")

    # ---- ABA 4: Grupos ----
    with tab4:
        with st.form("form_group"):
            nome_grupo = st.text_input("Nome do grupo/evento")
            col1, col2 = st.columns(2)
            inicio = col1.date_input("Check-in", value=date.today(), key="inicio_grupo")
            fim = col2.date_input("Check-out", value=date.today(), key="fim_grupo")
            col3, col4 = st.columns(2)
            quartos_bloq = col3.number_input("Quartos bloqueados", min_value=1, step=1)
            tarifa_negociada = col4.number_input("Tarifa negociada (R$, opcional)", min_value=0.0, step=1.0)

            if st.form_submit_button("Salvar grupo"):
                add_group_booking(
                    hotel_id=hotel_id, group_name=nome_grupo,
                    start_date=str(inicio), end_date=str(fim),
                    rooms_blocked=int(quartos_bloq),
                    negotiated_rate=tarifa_negociada or None,
                )
                st.success(f"Grupo '{nome_grupo}' salvo!")