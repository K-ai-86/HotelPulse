"""
Ingestão de dados do próprio hotel.

No MVP real, este módulo teria 3 caminhos possíveis, do mais simples
ao mais automatizado:

  1. MANUAL   -> gestor preenche uma planilha/formulário (mais rápido de lançar)
  2. IMPORT   -> hotel exporta CSV do PMS diariamente e o sistema importa
  3. API      -> integração direta com o PMS (Omnibees, HITS, etc.)

Comece pela opção 1 ou 2. A opção 3 só compensa quando você tiver
volume de clientes suficiente para justificar o custo de integração
com cada PMS (eles não são padronizados).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import execute, run_query


def upsert_hotel(name: str, city: str, total_rooms: int) -> int:
    """Cria o hotel se não existir e retorna o id."""
    existing = run_query(
        "SELECT id FROM hotels WHERE name = :name AND city = :city",
        {"name": name, "city": city},
    )
    if existing:
        return existing[0]["id"]

    execute(
        "INSERT INTO hotels (name, city, total_rooms) VALUES (:name, :city, :rooms)",
        {"name": name, "city": city, "rooms": total_rooms},
    )
    result = run_query(
        "SELECT id FROM hotels WHERE name = :name AND city = :city",
        {"name": name, "city": city},
    )
    return result[0]["id"]


def import_daily_data(hotel_id: int, date: str, occupancy_pct: float,
                       adr: float, rooms_available: int,
                       reservations_next_7d: int = None):
    """
    Importa (ou atualiza) os dados diários de um hotel.

    Pode ser chamado a partir de:
      - um endpoint de upload de CSV
      - um cron job que lê um arquivo compartilhado
      - uma integração futura com o PMS
    """
    existing = run_query(
        "SELECT id FROM hotel_daily_data WHERE hotel_id = :hid AND date = :date",
        {"hid": hotel_id, "date": date},
    )

    if existing:
        execute(
            """
            UPDATE hotel_daily_data
            SET occupancy_pct = :occ, adr = :adr,
                rooms_available = :rooms, reservations_next_7d = :res
            WHERE hotel_id = :hid AND date = :date
            """,
            {
                "occ": occupancy_pct, "adr": adr, "rooms": rooms_available,
                "res": reservations_next_7d, "hid": hotel_id, "date": date,
            },
        )
    else:
        execute(
            """
            INSERT INTO hotel_daily_data
                (hotel_id, date, occupancy_pct, adr, rooms_available, reservations_next_7d)
            VALUES (:hid, :date, :occ, :adr, :rooms, :res)
            """,
            {
                "hid": hotel_id, "date": date, "occ": occupancy_pct,
                "adr": adr, "rooms": rooms_available, "res": reservations_next_7d,
            },
        )


def import_from_csv(hotel_id: int, csv_path: str):
    """
    Caminho recomendado para o MVP: hotel exporta CSV do PMS
    com colunas: date, occupancy_pct, adr, rooms_available, reservations_next_7d
    """
    import pandas as pd
    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        import_daily_data(
            hotel_id=hotel_id,
            date=str(row["date"]),
            occupancy_pct=float(row["occupancy_pct"]),
            adr=float(row["adr"]),
            rooms_available=int(row["rooms_available"]),
            reservations_next_7d=int(row.get("reservations_next_7d", 0)),
        )
    print(f"[hotel_data] Importadas {len(df)} linhas do CSV para hotel_id={hotel_id}")
