"""
Orquestra o pipeline completo do HotelPulse MVP:

    DADOS DO HOTEL + CONCORRÊNCIA -> PostgreSQL -> Motor de Revenue -> Recomendação

Rode este script para: inicializar o banco, gerar dados de exemplo
(se ainda não existirem) e rodar o motor de revenue para todos os hotéis.

Depois, abra o dashboard com:
    streamlit run dashboard/app.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.database import init_db, run_query
from ingestion.mock_data_generator import generate_mock_data
from engine.revenue_engine import run_engine_for_hotel


def main():
    print("=== HotelPulse MVP — Pipeline ===\n")

    print("[1/3] Inicializando banco de dados...")
    init_db()

    hotels = run_query("SELECT id FROM hotels")
    if not hotels:
        print("\n[2/3] Nenhum hotel encontrado — gerando dados de exemplo...")
        generate_mock_data(days=14)
        hotels = run_query("SELECT id FROM hotels")
    else:
        print(f"\n[2/3] {len(hotels)} hotel(is) já cadastrado(s). Pulando geração de mock.")

    print("\n[3/3] Rodando motor de revenue management...")
    for h in hotels:
        run_engine_for_hotel(h["id"])

    print("\n✅ Pipeline concluído. Rode `streamlit run dashboard/app.py` para ver os resultados.")


if __name__ == "__main__":
    main()
