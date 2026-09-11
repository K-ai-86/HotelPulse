"""
Ingestão de reservas de grupo (bloqueio de quartos para eventos).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import execute, run_query


def add_group_booking(hotel_id: int, group_name: str, start_date: str,
                       end_date: str, rooms_blocked: int,
                       negotiated_rate: float = None, status: str = "confirmado"):
    execute(
        """
        INSERT INTO group_bookings
            (hotel_id, group_name, start_date, end_date, rooms_blocked, negotiated_rate, status)
        VALUES
            (:hid, :name, :start, :end, :rooms, :rate, :status)
        """,
        {
            "hid": hotel_id, "name": group_name, "start": start_date, "end": end_date,
            "rooms": rooms_blocked, "rate": negotiated_rate, "status": status,
        },
    )


def list_group_bookings(hotel_id: int):
    return run_query(
        "SELECT * FROM group_bookings WHERE hotel_id = :hid ORDER BY start_date",
        {"hid": hotel_id},
    )