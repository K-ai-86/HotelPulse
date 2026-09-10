-- =========================================================
-- HOTELPULSE MVP — SCHEMA
-- Compatível com PostgreSQL. Para SQLite (dev/testes),
-- database.py já adapta os tipos automaticamente via SQLAlchemy.
-- =========================================================

CREATE TABLE IF NOT EXISTS hotels (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    city            VARCHAR(255) NOT NULL,
    total_rooms     INTEGER NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dados diários do próprio hotel (vindos de PMS, planilha ou input manual)
CREATE TABLE IF NOT EXISTS hotel_daily_data (
    id                      SERIAL PRIMARY KEY,
    hotel_id                INTEGER NOT NULL REFERENCES hotels(id),
    date                    DATE NOT NULL,
    occupancy_pct           NUMERIC(5,2) NOT NULL,   -- ex: 82.50
    adr                     NUMERIC(10,2) NOT NULL,  -- Average Daily Rate (tarifa média)
    rooms_available         INTEGER NOT NULL,
    reservations_next_7d    INTEGER,
    UNIQUE(hotel_id, date)
);

-- Concorrentes cadastrados para cada hotel
CREATE TABLE IF NOT EXISTS competitors (
    id              SERIAL PRIMARY KEY,
    hotel_id        INTEGER NOT NULL REFERENCES hotels(id),
    name            VARCHAR(255) NOT NULL
);

-- Tarifas coletadas dos concorrentes (scraping, importação manual, etc.)
CREATE TABLE IF NOT EXISTS competitor_rates (
    id              SERIAL PRIMARY KEY,
    competitor_id   INTEGER NOT NULL REFERENCES competitors(id),
    date            DATE NOT NULL,
    rate            NUMERIC(10,2) NOT NULL,
    UNIQUE(competitor_id, date)
);

-- Eventos/feriados que impactam demanda (cadastro manual no MVP)
CREATE TABLE IF NOT EXISTS demand_events (
    id              SERIAL PRIMARY KEY,
    city            VARCHAR(255) NOT NULL,
    date            DATE NOT NULL,
    name            VARCHAR(255) NOT NULL,
    demand_impact   VARCHAR(20) NOT NULL  -- 'baixo' | 'medio' | 'alto'
);

-- Saída do motor de revenue: recomendações geradas
CREATE TABLE IF NOT EXISTS recommendations (
    id                      SERIAL PRIMARY KEY,
    hotel_id                INTEGER NOT NULL REFERENCES hotels(id),
    date                    DATE NOT NULL,
    current_rate            NUMERIC(10,2) NOT NULL,
    market_min              NUMERIC(10,2),
    market_max              NUMERIC(10,2),
    occupancy_pct           NUMERIC(5,2) NOT NULL,
    demand_level            VARCHAR(20) NOT NULL,   -- 'baixa' | 'media' | 'alta'
    action                  VARCHAR(20) NOT NULL,   -- 'aumentar' | 'manter' | 'promover'
    suggested_rate_min      NUMERIC(10,2),
    suggested_rate_max      NUMERIC(10,2),
    message                 TEXT NOT NULL,
    status                  VARCHAR(20) DEFAULT 'pendente', -- 'pendente' | 'aceita' | 'ignorada'
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(hotel_id, date)
);
