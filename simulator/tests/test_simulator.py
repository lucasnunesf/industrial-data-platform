"""Tests for the finance and logistics rules of the simulator. No database needed."""

import csv
from datetime import datetime
from pathlib import Path

import factory_config as cfg
import production

PTAX_FILE = Path(production.__file__).parent / "data" / "ptax_usd_brl.csv"


def test_freight_grows_with_distance_and_has_a_minimum():
    local = production.freight_cost("SP", 1000)
    near = production.freight_cost("MG", 1000)
    far = production.freight_cost("AM", 1000)
    assert local < near < far
    assert production.freight_cost("SP", 1) == cfg.FREIGHT_MINIMUM_BRL


def test_work_time_skips_nights_and_weekends():
    friday_afternoon = datetime(2026, 7, 3, 15, 0)  # one hour before the shift ends
    finish = production.add_work(friday_afternoon, 120)
    assert finish == datetime(2026, 7, 6, 8, 0)  # Monday, one hour into the shift


def test_ptax_file_covers_the_simulation_start():
    with PTAX_FILE.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    dates = [r["rate_date"] for r in rows]
    assert dates == sorted(set(dates))
    assert dates[0] <= cfg.START_DATE.isoformat()
    assert all(float(r["buy_rate"]) > 0 and float(r["sell_rate"]) > 0 for r in rows)
