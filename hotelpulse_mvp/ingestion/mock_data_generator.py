"""
Gera dados fictícios realistas para você testar o pipeline
completo (coleta -> banco -> motor -> recomendação -> dashboard)
antes de ter integrações reais.

Rode este script uma vez para popular o banco local.
"""

import sys
import os
import random
from datetime import date, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.hotel_data import upsert_hotel, import_daily_data
from ingestion.competitor_data import import_manual_batch

random.seed(42)


def generate_mock_data(days: int = 14):
    hotel_id = upsert_hotel(name="Hotel Exemplo", city="Teresina", total_rooms=50)

    today = date.today()
    competitor_names = ["Hotel Concorrente A", "Hotel Concorrente B", "Pousada Concorrente C"]

    for i in range(days):
        d = (today + timedelta(days=i)).isoformat()

        # Simula variação de ocupação e demanda ao longo dos dias
        base_occupancy = random.uniform(45, 90)
        occupancy = round(base_occupancy, 1)
        rooms_available = round(50 * (1 - occupancy / 100))
        adr = round(random.uniform(260, 300), 2)
        reservations_next_7d = random.randint(20, 90)

        import_daily_data(
            hotel_id=hotel_id,
            date=d,
            occupancy_pct=occupancy,
            adr=adr,
            rooms_available=rooms_available,
            reservations_next_7d=reservations_next_7d,
        )

        # Tarifas de concorrência: normalmente um pouco mais altas,
        # simulando o cenário de "hotel subprecificado" do documento original
        rates = {
            name: round(adr * random.uniform(1.05, 1.30), 2)
            for name in competitor_names
        }
        import_manual_batch(hotel_id=hotel_id, date=d, rates=rates)

    _generate_mock_events(hotel_id, today, days)

    print(f"[mock_data] {days} dias de dados gerados para hotel_id={hotel_id}")
    return hotel_id


def _generate_mock_events(hotel_id: int, today: date, days: int):
    """Popula demand_events com alguns eventos fictícios para a cidade do hotel."""
    from db.database import run_query, execute

    hotel = run_query("SELECT city FROM hotels WHERE id = :hid", {"hid": hotel_id})[0]
    city = hotel["city"]

    sample_events = [
        (5, "Evento corporativo (Congresso)", "alto"),
        (8, "Show no Centro de Convenções", "alto"),
        (10, "Feriado municipal", "medio"),
        (15, "Show nacional (Arena)", "alto"),
    ]

    for offset, name, impact in sample_events:
        if offset >= days:
            continue
        event_date = (today + timedelta(days=offset)).isoformat()
        existing = run_query(
            "SELECT id FROM demand_events WHERE city = :city AND date = :date AND name = :name",
            {"city": city, "date": event_date, "name": name},
        )
        if not existing:
            execute(
                "INSERT INTO demand_events (city, date, name, demand_impact) VALUES (:city, :date, :name, :impact)",
                {"city": city, "date": event_date, "name": name, "impact": impact},
            )


if __name__ == "__main__":
    from db.database import init_db
    init_db()
    generate_mock_data()
