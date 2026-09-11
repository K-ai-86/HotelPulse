"""
MOTOR DE REVENUE MANAGEMENT

Este é o coração do HotelPulse. Segue a recomendação da seção 18
do projeto original: comece com REGRAS + ESTATÍSTICA, não com uma
IA sofisticada. É mais barato, mais previsível e mais fácil de
explicar/depurar quando uma recomendação parecer estranha.

Fluxo:
  1. Carrega dados do hotel (pandas)
  2. Carrega dados de concorrência e agrega (média/min/max) por data
  3. Aplica as regras de decisão
  4. Gera recomendação estruturada + mensagem em linguagem natural
  5. Grava no banco (tabela recommendations)
"""

import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import run_query, execute
from config import RULES


def load_hotel_data(hotel_id: int) -> pd.DataFrame:
    rows = run_query(
        "SELECT * FROM hotel_daily_data WHERE hotel_id = :hid ORDER BY date",
        {"hid": hotel_id},
    )
    return pd.DataFrame(rows)


def load_competitor_data(hotel_id: int) -> pd.DataFrame:
    rows = run_query(
        """
        SELECT cr.date, cr.rate, c.name AS competitor_name
        FROM competitor_rates cr
        JOIN competitors c ON c.id = cr.competitor_id
        WHERE c.hotel_id = :hid
        ORDER BY cr.date
        """,
        {"hid": hotel_id},
    )
    return pd.DataFrame(rows)


def aggregate_competitor_rates(comp_df: pd.DataFrame) -> pd.DataFrame:
    """Agrega tarifas de concorrência por data: média, mínimo, máximo."""
    if comp_df.empty:
        return pd.DataFrame(columns=["date", "market_avg", "market_min", "market_max"])

    agg = comp_df.groupby("date")["rate"].agg(
        market_avg="mean", market_min="min", market_max="max"
    ).reset_index()
    return agg


def classify_demand(row, rules) -> str:
    """Classifica o nível de demanda com base em ocupação e reservas futuras."""
    if row["occupancy_pct"] >= rules["high_occupancy_threshold"]:
        return "alta"
    if row["occupancy_pct"] <= rules["low_occupancy_threshold"]:
        return "baixa"
    return "media"


def decide_action(row, rules) -> dict:
    """
    Aplica as regras de decisão do MVP (seção 18 do doc original):

        Se ocupação > threshold_alto
        e concorrência > tarifa atual em X%
        e poucos quartos disponíveis
        -> recomendar AUMENTO

        Se ocupação < threshold_baixo
        e concorrência não está muito acima
        -> recomendar PROMOÇÃO (desconto)

        Caso contrário
        -> MANTER
    """
    current_rate = row["adr"]
    market_avg = row.get("market_avg")
    occupancy = row["occupancy_pct"]
    rooms_available = row["rooms_available"]
    total_rooms = row.get("total_rooms", None)

    demand_level = classify_demand(row, rules)

    availability_pct = None
    if total_rooms:
        availability_pct = (rooms_available / total_rooms) * 100

    competitor_premium = None
    if market_avg and current_rate:
        competitor_premium = (market_avg - current_rate) / current_rate

    # Regra 1: AUMENTAR
    if (
        demand_level == "alta"
        and competitor_premium is not None
        and competitor_premium >= rules["competitor_premium_threshold"]
        and (availability_pct is None or availability_pct <= rules["low_availability_pct"])
    ):
        low, high = rules["increase_range"]
        suggested_min = round(current_rate * (1 + low), 2)
        suggested_max = round(current_rate * (1 + high), 2)
        return {
            "action": "aumentar",
            "demand_level": demand_level,
            "suggested_rate_min": suggested_min,
            "suggested_rate_max": suggested_max,
        }

    # Regra 2: PROMOVER (desconto para estimular demanda fraca)
    if demand_level == "baixa" and (competitor_premium is None or competitor_premium < 0.05):
        low, high = rules["discount_range"]
        suggested_min = round(current_rate * (1 - high), 2)
        suggested_max = round(current_rate * (1 - low), 2)
        return {
            "action": "promover",
            "demand_level": demand_level,
            "suggested_rate_min": suggested_min,
            "suggested_rate_max": suggested_max,
        }

    # Regra 3: MANTER
    return {
        "action": "manter",
        "demand_level": demand_level,
        "suggested_rate_min": current_rate,
        "suggested_rate_max": current_rate,
    }


def build_message(hotel_name: str, date_str: str, row: dict, decision: dict) -> str:
    """Gera a mensagem em linguagem natural (o que hoje seria a camada de IA)."""
    action = decision["action"]
    current_rate = row["adr"]
    market_min = row.get("market_min")
    market_max = row.get("market_max")

    market_str = ""
    if market_min and market_max:
        market_str = f"Mercado: R$ {market_min:.0f}–{market_max:.0f}\n"

    if action == "aumentar":
        header = "🔴 Oportunidade de aumento de tarifa"
        rec = f"Sugestão: aumentar para R$ {decision['suggested_rate_min']:.0f}–{decision['suggested_rate_max']:.0f}."
    elif action == "promover":
        header = "🟡 Risco de baixa ocupação"
        rec = f"Sugestão: criar promoção, faixa R$ {decision['suggested_rate_min']:.0f}–{decision['suggested_rate_max']:.0f}."
    else:
        header = "🟢 Tarifa adequada"
        rec = "Sugestão: manter tarifa atual."

    return (
        f"{header}\n\n"
        f"Hotel: {hotel_name}\n"
        f"Data: {date_str}\n"
        f"Ocupação: {row['occupancy_pct']:.0f}%\n"
        f"Sua tarifa: R$ {current_rate:.0f}\n"
        f"{market_str}"
        f"Demanda prevista: {decision['demand_level']}\n\n"
        f"💡 {rec}"
    )


def run_engine_for_hotel(hotel_id: int):
    """
    Ponto de entrada principal: roda o motor completo para um hotel
    e grava as recomendações no banco.
    """
    hotel_info = run_query("SELECT * FROM hotels WHERE id = :hid", {"hid": hotel_id})
    if not hotel_info:
        raise ValueError(f"Hotel {hotel_id} não encontrado")
    hotel = hotel_info[0]

    hotel_df = load_hotel_data(hotel_id)
    if hotel_df.empty:
        print(f"[revenue_engine] Sem dados para hotel_id={hotel_id}")
        return []

    comp_df = load_competitor_data(hotel_id)
    comp_agg = aggregate_competitor_rates(comp_df)

    merged = hotel_df.merge(comp_agg, on="date", how="left")
    merged["total_rooms"] = hotel["total_rooms"]

    results = []
    for _, row in merged.iterrows():
        decision = decide_action(row, RULES)
        message = build_message(hotel["name"], str(row["date"]), row, decision)

        results.append({
            "hotel_id": hotel_id,
            "date": str(row["date"]),
            "current_rate": float(row["adr"]),
            "market_min": float(row["market_min"]) if pd.notna(row.get("market_min")) else None,
            "market_max": float(row["market_max"]) if pd.notna(row.get("market_max")) else None,
            "occupancy_pct": float(row["occupancy_pct"]),
            "demand_level": decision["demand_level"],
            "action": decision["action"],
            "suggested_rate_min": decision["suggested_rate_min"],
            "suggested_rate_max": decision["suggested_rate_max"],
            "message": message,
        })

        _save_recommendation(results[-1])

    print(f"[revenue_engine] {len(results)} recomendações geradas para hotel_id={hotel_id}")
    return results


def _save_recommendation(rec: dict):
    existing = run_query(
        "SELECT id FROM recommendations WHERE hotel_id = :hid AND date = :date",
        {"hid": rec["hotel_id"], "date": rec["date"]},
    )
    if existing:
        execute(
            """
            UPDATE recommendations SET
                current_rate = :current_rate, market_min = :market_min, market_max = :market_max,
                occupancy_pct = :occupancy_pct, demand_level = :demand_level, action = :action,
                suggested_rate_min = :suggested_rate_min, suggested_rate_max = :suggested_rate_max,
                message = :message
            WHERE hotel_id = :hotel_id AND date = :date
            """,
            rec,
        )
    else:
        execute(
            """
            INSERT INTO recommendations
                (hotel_id, date, current_rate, market_min, market_max, occupancy_pct,
                 demand_level, action, suggested_rate_min, suggested_rate_max, message)
            VALUES
                (:hotel_id, :date, :current_rate, :market_min, :market_max, :occupancy_pct,
                 :demand_level, :action, :suggested_rate_min, :suggested_rate_max, :message)
            """,
            rec,
        )


def compute_dashboard_summary(hotel_id: int) -> dict:
    """
    Calcula os números agregados usados no topo do dashboard:
    ocupação média, ADR médio, RevPAR médio, receita total, diárias
    vendidas, e a variação (%) de cada métrica vs. a primeira metade
    do período disponível (proxy simples de "mês anterior" enquanto
    não há histórico de meses completos).
    """
    hotel = run_query("SELECT * FROM hotels WHERE id = :hid", {"hid": hotel_id})[0]
    df = load_hotel_data(hotel_id)

    if df.empty:
        return {}

    df["adr"] = df["adr"].astype(float)
    df["occupancy_pct"] = df["occupancy_pct"].astype(float)
    df["revpar"] = df["adr"] * df["occupancy_pct"] / 100
    df["rooms_sold"] = (df["occupancy_pct"] / 100 * hotel["total_rooms"]).round()

    midpoint = max(len(df) // 2, 1)
    recent = df.iloc[midpoint:]
    previous = df.iloc[:midpoint]

    def pct_change(new_val, old_val):
        if not old_val:
            return 0.0
        return round(((new_val - old_val) / old_val) * 100, 1)

    latest = df.iloc[-1]

    summary = {
        "hotel_name": hotel["name"],
        "city": hotel["city"],
        "total_rooms": hotel["total_rooms"],
        "occupancy_avg": round(recent["occupancy_pct"].mean(), 1),
        "occupancy_delta": pct_change(recent["occupancy_pct"].mean(), previous["occupancy_pct"].mean()),
        "adr_avg": round(recent["adr"].mean(), 0),
        "adr_delta": pct_change(recent["adr"].mean(), previous["adr"].mean()),
        "revpar_avg": round(recent["revpar"].mean(), 0),
        "revpar_delta": pct_change(recent["revpar"].mean(), previous["revpar"].mean()),
        "rooms_available_latest": int(latest["rooms_available"]),
        "revenue_total": round((df["adr"] * df["rooms_sold"]).sum(), 0),
        "rooms_sold_total": int(df["rooms_sold"].sum()),
        "occupancy_month_avg": round(df["occupancy_pct"].mean(), 1),
        "adr_month_avg": round(df["adr"].mean(), 0),
    }
    return summary


def compute_competitive_position(hotel_id: int, on_date: str = None) -> pd.DataFrame:
    """Retorna tabela comparando a tarifa do hotel com cada concorrente numa data."""
    hotel_df = load_hotel_data(hotel_id)
    comp_df = load_competitor_data(hotel_id)
    hotel_info = run_query("SELECT name FROM hotels WHERE id = :hid", {"hid": hotel_id})[0]

    if hotel_df.empty or comp_df.empty:
        return pd.DataFrame()

    target_date = on_date or hotel_df["date"].iloc[-1]
    own_rate = float(hotel_df[hotel_df["date"] == target_date]["adr"].iloc[0])

    day_comp = comp_df[comp_df["date"] == target_date].copy()
    day_comp["diff_pct"] = ((day_comp["rate"] - own_rate) / own_rate * 100).round(1)

    rows = [{"hotel": f"Seu hotel ({hotel_info['name']})", "rate": own_rate, "diff_pct": 0.0, "is_own": True}]
    for _, r in day_comp.iterrows():
        rows.append({
            "hotel": r["competitor_name"], "rate": float(r["rate"]),
            "diff_pct": float(r["diff_pct"]), "is_own": False,
        })

    return pd.DataFrame(rows)


def get_top_opportunity_message(hotel_id: int) -> str:
    """Gera a frase-resumo (estilo 'citação') com a maior oportunidade em aberto."""
    recs = run_query(
        """
        SELECT * FROM recommendations
        WHERE hotel_id = :hid AND action = 'aumentar' AND status = 'pendente'
        ORDER BY date LIMIT 1
        """,
        {"hid": hotel_id},
    )
    if not recs:
        return "Sem oportunidades relevantes de ajuste de tarifa nos próximos dias."

    r = recs[0]
    upside_pct = round(((r["suggested_rate_max"] - r["current_rate"]) / r["current_rate"]) * 100)
    return (
        f"Com base nos dados atuais, seu hotel está subprecificado para a demanda "
        f"do dia {r['date']}. Ajustar a tarifa pode aumentar sua receita em até {upside_pct}%."
    )


if __name__ == "__main__":
    # Exemplo: roda o motor para o primeiro hotel cadastrado
    hotels = run_query("SELECT id FROM hotels LIMIT 1")
    if hotels:
        run_engine_for_hotel(hotels[0]["id"])
    else:
        print("Nenhum hotel cadastrado. Rode mock_data_generator.py primeiro.")
