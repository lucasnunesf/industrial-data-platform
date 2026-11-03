"""Simulation parameters. Fixed factory layout lives in erp/seed.sql."""

from datetime import date

SEED = 42
START_DATE = date(2026, 7, 1)
TIMEZONE = "America/Sao_Paulo"

SHIFT_START_HOUR = 7
SHIFT_END_HOUR = 16
WORKDAYS = {0, 1, 2, 3, 4}

N_CUSTOMERS = 40
N_PRODUCTS = 30

ORDERS_PER_DAY = (2, 6)
ITEMS_PER_ORDER = (1, 4)
QUANTITY_PER_ITEM = (5, 40)
PROMISED_DAYS = (7, 30)

MATERIALS = [
    ("CS-1020-2", "Carbon steel SAE 1020 2mm", 2.00, 7.85, 9.0),
    ("CS-1020-3", "Carbon steel SAE 1020 3mm", 3.00, 7.85, 9.0),
    ("CS-1020-6", "Carbon steel SAE 1020 6mm", 6.00, 7.85, 9.0),
    ("SS-304-1", "Stainless steel AISI 304 1.5mm", 1.50, 8.00, 32.0),
    ("SS-304-3", "Stainless steel AISI 304 3mm", 3.00, 8.00, 32.0),
    ("AL-5052-2", "Aluminum 5052 2mm", 2.00, 2.68, 38.0),
    ("AL-5052-4", "Aluminum 5052 4mm", 4.00, 2.68, 38.0),
]

PART_TYPES = ["Bracket", "Base plate", "Frame", "Guard", "Support",
              "Panel", "Flange", "Cover", "Enclosure", "Rack"]

ROUTING_WEIGHTS = {"CUT_ONLY": 0.40, "CUT_FAB": 0.35, "FULL": 0.25}

OPERATORS = [
    ("CUT", "machine_operator", 2),
    ("CUT", "unloader", 2),
    ("FAB", "welder", 5),
    ("FAB", "assembler", 5),
    ("FIN", "finisher", 5),
    ("QC", "inspector", 1),
]

# Minutes per unit at each work center (scaled by part weight) and setup minutes.
MINUTES_PER_UNIT = {"CUT": 2.2, "WELD": 3.5, "FAB": 12.0, "FIN": 6.0}
SETUP_MINUTES = {"CUT": 20, "WELD": 15, "FAB": 10, "FIN": 5}
PARALLEL_SLOTS = {"CUT": 2, "WELD": 1, "FAB": 10, "FIN": 5}
SCRAP_RATE = {"CUT": 0.03, "WELD": 0.01, "FAB": 0.015, "FIN": 0.005}

INSPECTION_RATE = 0.20
