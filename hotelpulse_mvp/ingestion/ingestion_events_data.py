"""
Ingestão de eventos e feriados que afetam demanda.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import execute, run_query


def add_event(city: str, date: str, name: str, demand_impact: str):
    """
    demand_impact deve ser: 'baixo', 'medio' ou 'alto'
    (feriados normalmente são 'medio', shows/congressos costumam ser 'alto')
    """
    execute(
        "INSERT INTO demand_events (city, date, name, demand_impact) VALUES (:city, :date, :name, :impact)",
        {"city": city, "date": date, "name": name, "impact": demand_impact},
    )


def list_events(city: str):
    return run_query(
        "SELECT * FROM demand_events WHERE city = :city ORDER BY date",
        {"city": city},
    )