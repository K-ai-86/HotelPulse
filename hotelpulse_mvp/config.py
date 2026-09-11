"""
Configuração central do HotelPulse MVP.

Por padrão usa SQLite local (hotelpulse.db) para você testar tudo
sem precisar de um servidor Postgres rodando.

Para usar Postgres em produção, defina a variável de ambiente:
    export DATABASE_URL="postgresql+psycopg2://usuario:senha@host:5432/hotelpulse"
"""

import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///hotelpulse.db"
)

# ---- Parâmetros do motor de revenue (regras do MVP) ----
# Ver seção 18 do documento original: regras simples antes de IA sofisticada.

RULES = {
    # Ocupação acima disso = sinal de demanda forte
    "high_occupancy_threshold": 75.0,
    # Ocupação abaixo disso = sinal de demanda fraca
    "low_occupancy_threshold": 40.0,
    # Quanto a concorrência precisa estar acima da sua tarifa (%) para
    # recomendar aumento
    "competitor_premium_threshold": 0.10,
    # Percentual de quartos disponíveis abaixo do qual reforça o sinal
    # de "vender mais caro, está acabando"
    "low_availability_pct": 20.0,
    # Ajuste sugerido quando o motor recomenda aumento (faixa %)
    "increase_range": (0.08, 0.15),
    # Desconto sugerido quando o motor recomenda promoção (faixa %)
    "discount_range": (0.10, 0.20),
}
