# HotelPulse MVP

Implementação da arquitetura:

```
DADOS DO HOTEL   CONCORRÊNCIA
        └───────┬───────┘
              PostgreSQL
                  ↓
            Python/Pandas
                  ↓
         MOTOR DE REVENUE
                  ↓
           RECOMENDAÇÃO
                  ↓
             Dashboard
```

## Como rodar

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Rodar o pipeline completo (cria banco, gera dados de exemplo, roda o motor)
python main.py

# 3. Abrir o dashboard
streamlit run dashboard/app.py
```

Por padrão usa **SQLite local** (`hotelpulse.db`) — zero configuração,
ótimo para testar hoje mesmo. Para produção, defina:

```bash
export DATABASE_URL="postgresql+psycopg2://usuario:senha@host:5432/hotelpulse"
```

e rode `python main.py` de novo — o schema é criado automaticamente.

## Estrutura

| Pasta/arquivo | Responsabilidade |
|---|---|
| `db/schema.sql` | Modelo de dados (hotéis, dados diários, concorrentes, tarifas, recomendações) |
| `db/database.py` | Conexão e execução de queries |
| `ingestion/hotel_data.py` | Entrada de dados do hotel (manual, CSV, ou futura API do PMS) |
| `ingestion/competitor_data.py` | Entrada de dados de concorrência (manual por enquanto — ver nota abaixo) |
| `ingestion/mock_data_generator.py` | Gera dados fictícios para testar tudo hoje |
| `engine/revenue_engine.py` | Regras de decisão (aumentar/manter/promover) + geração da mensagem |
| `dashboard/app.py` | Dashboard com os 4 módulos: Visão do hotel, Concorrência, Demanda, Recomendações |
| `main.py` | Roda o pipeline inteiro de ponta a ponta |

## Decisões importantes tomadas neste MVP

1. **Coleta de concorrência é manual no início.** Scraping de OTAs quebra
   com frequência e traz risco de bloqueio/ToS. `import_manual_batch()`
   deixa isso rápido (5 min/dia) enquanto você valida se o hotel paga
   pelo produto. Automatize só depois.

2. **"IA" = regras + estatística, não modelo complexo.** O motor em
   `revenue_engine.py` implementa exatamente as regras da seção 18 do
   projeto original. Ajuste os limiares em `config.py` (`RULES`) sem
   tocar no código.

3. **Recomendação, não decisão automática.** O motor nunca altera
   tarifa sozinho — grava uma recomendação com status `pendente` que
   o gestor aceita ou ignora (botões já no dashboard, só falta ligar
   ao update do banco).

4. **SQLite → Postgres é só trocar variável de ambiente.** Não há
   código específico de um banco; SQLAlchemy abstrai isso.

## Próximos passos sugeridos

- [ ] Trocar mock por importação real de CSV do primeiro hotel piloto
- [ ] Cadastrar concorrentes reais e alimentar manualmente por 2 semanas
- [ ] Ligar botões "Aceitar/Ignorar" ao update da tabela `recommendations`
      (para começar a medir acerto das recomendações — seção 20 do doc)
- [ ] Adicionar envio do resumo semanal por WhatsApp (Twilio/360dialog)
- [ ] Cadastrar `demand_events` (feriados, eventos locais) para refinar
      a classificação de demanda
