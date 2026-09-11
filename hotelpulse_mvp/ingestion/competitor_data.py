"""
Ingestão de dados de concorrência.

ATENÇÃO — este é o ponto mais frágil do projeto na prática:
  - Scraping direto de OTAs (Booking, Decolar, etc.) quebra com frequência
    e pode violar termos de uso.
  - No MVP, o caminho mais seguro e rápido é registro MANUAL diário
    (você ou o próprio gestor olha 3-5 concorrentes e digita o preço,
    leva 5 minutos por dia).
  - Automação real (scraping ou parceria com um provedor de rate
    shopping, ex: OTA Insight / Lighthouse) só vale a pena depois de
    validar que o cliente paga pelo produto.

Este módulo já está desenhado para aceitar qualquer uma das fontes
sem mudar o resto do sistema.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import execute, run_query


def add_competitor(hotel_id: int, name: str) -> int:
    existing = run_query(
        "SELECT id FROM competitors WHERE hotel_id = :hid AND name = :name",
        {"hid": hotel_id, "name": name},
    )
    if existing:
        return existing[0]["id"]

    execute(
        "INSERT INTO competitors (hotel_id, name) VALUES (:hid, :name)",
        {"hid": hotel_id, "name": name},
    )
    result = run_query(
        "SELECT id FROM competitors WHERE hotel_id = :hid AND name = :name",
        {"hid": hotel_id, "name": name},
    )
    return result[0]["id"]


def import_rate(competitor_id: int, date: str, rate: float):
    """Registra (ou atualiza) a tarifa de um concorrente numa data."""
    existing = run_query(
        "SELECT id FROM competitor_rates WHERE competitor_id = :cid AND date = :date",
        {"cid": competitor_id, "date": date},
    )
    if existing:
        execute(
            "UPDATE competitor_rates SET rate = :rate WHERE competitor_id = :cid AND date = :date",
            {"rate": rate, "cid": competitor_id, "date": date},
        )
    else:
        execute(
            "INSERT INTO competitor_rates (competitor_id, date, rate) VALUES (:cid, :date, :rate)",
            {"cid": competitor_id, "date": date, "rate": rate},
        )


def import_manual_batch(hotel_id: int, date: str, rates: dict):
    """
    Forma mais rápida de alimentar o MVP no dia a dia:

        import_manual_batch(hotel_id=1, date="2026-09-15", rates={
            "Hotel Concorrente A": 320.0,
            "Hotel Concorrente B": 345.0,
            "Pousada Concorrente C": 298.0,
        })
    """
    for name, rate in rates.items():
        cid = add_competitor(hotel_id, name)
        import_rate(cid, date, rate)
    print(f"[competitor_data] {len(rates)} tarifas registradas para {date}")


# ---- Stub para scraping futuro (não implementado no MVP) ----
def scrape_ota_rates(competitor_url: str, date: str):
    """
    Placeholder para uma futura automação de coleta.
    Não implementado no MVP — mantenha coleta manual até validar o negócio.
    """
    raise NotImplementedError(
        "Scraping automático ainda não implementado. "
        "Use import_manual_batch() enquanto valida o produto."
    )
