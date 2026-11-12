"""Generate orders and shop-floor execution up to a cut-off time.

The history is deterministic: running again with a later cut-off reproduces the
same past and only adds what happened since, so re-runs behave like a live ERP
(new rows, status updates) and work with incremental extraction.
"""

import random
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import factory_config as cfg

TZ = ZoneInfo(cfg.TIMEZONE)
SHIFT_MINUTES = (cfg.SHIFT_END_HOUR - cfg.SHIFT_START_HOUR) * 60


def to_work(dt: datetime) -> datetime:
    while True:
        start = dt.replace(hour=cfg.SHIFT_START_HOUR, minute=0, second=0, microsecond=0)
        end = dt.replace(hour=cfg.SHIFT_END_HOUR, minute=0, second=0, microsecond=0)
        if dt.weekday() in cfg.WORKDAYS and dt < end:
            return max(dt, start)
        dt = start + timedelta(days=1)


def add_work(dt: datetime, minutes: float) -> datetime:
    dt = to_work(dt)
    while True:
        end = dt.replace(hour=cfg.SHIFT_END_HOUR, minute=0, second=0, microsecond=0)
        available = (end - dt).total_seconds() / 60
        if minutes <= available:
            return dt + timedelta(minutes=minutes)
        minutes -= available
        dt = to_work(end)


def freight_cost(state: str, weight_kg: float) -> float:
    """Freight of one shipment: a rate per kg by distance from the plant, with a minimum charge."""
    if state == cfg.PLANT_STATE:
        region = "local"
    elif state in cfg.NEAR_STATES:
        region = "near"
    else:
        region = "far"
    return round(max(cfg.FREIGHT_MINIMUM_BRL, weight_kg * cfg.FREIGHT_BRL_PER_KG[region]), 2)


def load_context(conn) -> dict:
    ctx = {}
    customers = conn.execute("SELECT customer_id, state FROM customers ORDER BY cnpj").fetchall()
    ctx["customers"] = [r[0] for r in customers]
    ctx["customer_state"] = dict(customers)
    price = {m[0]: m[4] for m in cfg.MATERIALS}
    ctx["products"] = [
        (pid, routing, float(weight), price.get(mcode, 10.0))
        for pid, routing, weight, mcode in conn.execute(
            """SELECT p.product_id, r.routing_code, p.product_unit_weight_kg, m.material_code
               FROM products p
               JOIN routings r USING (routing_id)
               JOIN materials m USING (material_id)
               ORDER BY p.product_code""")
    ]
    steps = defaultdict(list)
    for routing, step_id, wc in conn.execute(
            """SELECT r.routing_code, rs.routing_step_id, wc.work_center_code
               FROM routing_steps rs
               JOIN routings r USING (routing_id)
               JOIN work_centers wc USING (work_center_id)
               ORDER BY r.routing_code, rs.step_sequence"""):
        steps[routing].append((step_id, wc))
    ctx["steps"] = steps
    machines = defaultdict(list)
    for wc, mid in conn.execute(
            """SELECT wc.work_center_code, m.machine_id FROM machines m
               JOIN work_centers wc USING (work_center_id) ORDER BY m.machine_code"""):
        machines[wc].append(mid)
    ctx["machines"] = machines
    operators = defaultdict(list)
    for role, oid in conn.execute(
            "SELECT operator_role, operator_id FROM operators ORDER BY operator_id"):
        operators[role].append(oid)
    ctx["operators"] = operators
    return ctx


def slot_resources(ctx: dict) -> dict:
    ops = ctx["operators"]
    fab_team = ops["welder"] + ops["assembler"]
    res = {}
    for wc, n in cfg.PARALLEL_SLOTS.items():
        res[wc] = []
        for i in range(n):
            machine = ctx["machines"][wc][i] if i < len(ctx["machines"][wc]) else None
            if wc == "CUT":
                operator = ops["machine_operator"][i % len(ops["machine_operator"])]
            elif wc == "WELD":
                operator = ops["welder"][0]
            elif wc == "FAB":
                operator = fab_team[i % len(fab_team)]
            else:
                operator = ops["finisher"][i % len(ops["finisher"])]
            res[wc].append((machine, operator))
    return res


def simulate(ctx: dict, until: datetime) -> dict:
    out = defaultdict(list)
    resources = slot_resources(ctx)
    first_shift = datetime.combine(cfg.START_DATE, datetime.min.time()).replace(
        hour=cfg.SHIFT_START_HOUR)
    free_at = {wc: [first_shift] * n for wc, n in cfg.PARALLEL_SLOTS.items()}
    inspector = ctx["operators"]["inspector"][0]
    so_seq = 0
    day = cfg.START_DATE

    while day <= until.date():
        if day.weekday() not in cfg.WORKDAYS:
            day += timedelta(days=1)
            continue
        rng = random.Random(f"{cfg.SEED}-{day}")
        offsets = sorted(rng.uniform(0, SHIFT_MINUTES) for _ in range(rng.randint(*cfg.ORDERS_PER_DAY)))
        for offset in offsets:
            ordered_at = first_shift.replace(year=day.year, month=day.month, day=day.day) + timedelta(minutes=offset)
            if ordered_at > until:
                break
            so_seq += 1
            so_number = f"SO-{so_seq:06d}"
            promised = day + timedelta(days=rng.randint(*cfg.PROMISED_DAYS))
            lines_done, lines_started = [], []
            order_weight = 0.0

            for line in range(1, rng.randint(*cfg.ITEMS_PER_ORDER) + 1):
                pid, routing, weight, kg_price = rng.choice(ctx["products"])
                qty = rng.randint(*cfg.QUANTITY_PER_ITEM)
                price = round(weight * kg_price * 2.2 + 15 + rng.uniform(0, 10), 2)
                out["items"].append((so_number, line, pid, qty, price))
                order_weight += qty * weight

                po_number = f"PO-{so_seq:06d}-{line}"
                released_at = add_work(ordered_at, rng.uniform(60, 600))
                due = max(promised - timedelta(days=1), released_at.date())
                ready = released_at
                first_start = None
                units = qty  # units entering the next stage: the good output of the previous one

                for step_id, wc in ctx["steps"][routing]:
                    k = min(range(len(free_at[wc])), key=lambda i: free_at[wc][i])
                    start = to_work(max(ready, free_at[wc][k]))
                    minutes = (cfg.SETUP_MINUTES[wc] + units * cfg.MINUTES_PER_UNIT[wc]
                               * (0.5 + weight / 10) * rng.lognormvariate(0, 0.25))
                    finish = add_work(start, minutes)
                    free_at[wc][k] = finish
                    # One draw per planned unit keeps the random sequence, and so the rest of the
                    # history, unchanged; only the units that reached this stage can be scrapped.
                    draws = [rng.random() for _ in range(qty)]
                    scrap = sum(d < cfg.SCRAP_RATE[wc] for d in draws[:units])
                    machine, operator = resources[wc][k]
                    if wc == "WELD":
                        operator = rng.choice(ctx["operators"]["welder"])
                    out["events"].append((po_number, step_id, "start", start, machine, operator, None, None, None))
                    # work_minutes is the working time reported for the stage (no nights or weekends).
                    out["events"].append((po_number, step_id, "finish", finish, machine, operator,
                                          units - scrap, scrap, round(minutes, 1)))
                    first_start = first_start or start
                    ready = finish
                    units -= scrap

                last_finish = ready
                if rng.random() < cfg.INSPECTION_RATE:
                    inspected_at = add_work(ready, rng.uniform(30, 240))
                    sample = max(1, round(units * 0.2))
                    draws = [rng.random() for _ in range(max(1, round(qty * 0.2)))]
                    rejected = sum(d < 0.04 for d in draws[:sample])
                    result = "approved" if rejected == 0 else ("rework" if rejected <= 2 else "rejected")
                    out["inspections"].append((po_number, inspector, inspected_at, sample, rejected, result))
                    ready = inspected_at

                if last_finish <= until:
                    status = "completed"
                elif first_start <= until:
                    status = "in_progress"
                elif released_at <= until:
                    status = "released"
                else:
                    status = "planned"
                out["pos"].append((po_number, so_number, line, qty, released_at.date(), due, status))
                lines_done.append(ready)
                lines_started.append(first_start)

            shipped_at = add_work(max(lines_done), rng.uniform(60, 540))
            delivered_at = (shipped_at + timedelta(days=rng.randint(1, 3))).replace(
                hour=rng.randint(9, 15), minute=rng.randint(0, 59))
            if shipped_at <= until:
                so_status = "shipped"
            elif min(lines_started) <= until:
                so_status = "in_production"
            else:
                so_status = "open"
            customer = rng.choice(ctx["customers"])
            if so_status == "shipped":
                delivered = delivered_at if delivered_at <= until else None
                freight = freight_cost(ctx["customer_state"][customer], order_weight)
                out["shipments"].append((f"SH-{so_seq:06d}", so_number, shipped_at, delivered,
                                         "delivered" if delivered else "shipped", freight))
            out["orders"].append((so_number, customer, day, promised, so_status))
        day += timedelta(days=1)

    out["events"] = [e for e in out["events"] if e[3] <= until]
    out["inspections"] = [i for i in out["inspections"] if i[2] <= until]
    return out


def aware(dt):
    return dt.replace(tzinfo=TZ) if dt else None


def write(conn, data: dict) -> dict:
    cur = conn.cursor()
    cur.executemany(
        """INSERT INTO sales_orders (sales_order_number, customer_id, order_date,
                                     promised_date, sales_order_status)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (sales_order_number) DO UPDATE
               SET sales_order_status = EXCLUDED.sales_order_status
               WHERE sales_orders.sales_order_status IS DISTINCT FROM EXCLUDED.sales_order_status""",
        data["orders"])
    so_ids = dict(conn.execute("SELECT sales_order_number, sales_order_id FROM sales_orders"))

    cur.executemany(
        """INSERT INTO sales_order_items (sales_order_id, line_number, product_id,
                                          quantity, unit_price_brl)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (sales_order_id, line_number) DO NOTHING""",
        [(so_ids[so], line, pid, qty, price) for so, line, pid, qty, price in data["items"]])
    item_ids = {(so, line): iid for so, line, iid in conn.execute(
        """SELECT so.sales_order_number, i.line_number, i.sales_order_item_id
           FROM sales_order_items i JOIN sales_orders so USING (sales_order_id)""")}

    cur.executemany(
        """INSERT INTO production_orders (production_order_number, sales_order_item_id,
                                          planned_quantity, planned_start_date, due_date,
                                          production_order_status)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT (production_order_number) DO UPDATE
               SET production_order_status = EXCLUDED.production_order_status
               WHERE production_orders.production_order_status
                     IS DISTINCT FROM EXCLUDED.production_order_status""",
        [(po, item_ids[(so, line)], qty, start, due, status)
         for po, so, line, qty, start, due, status in data["pos"]])
    po_ids = dict(conn.execute(
        "SELECT production_order_number, production_order_id FROM production_orders"))

    cur.executemany(
        """INSERT INTO production_stage_events (production_order_id, routing_step_id, event_type,
                                                event_ts, machine_id, operator_id,
                                                good_quantity, scrap_quantity, work_minutes)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (production_order_id, routing_step_id, event_type) DO NOTHING""",
        [(po_ids[po], step, etype, aware(ts), m, o, good, scrap, minutes)
         for po, step, etype, ts, m, o, good, scrap, minutes in data["events"]])

    cur.executemany(
        """INSERT INTO quality_inspections (production_order_id, inspector_id, inspected_at,
                                            quantity_inspected, quantity_rejected, inspection_result)
           SELECT %s, %s, %s, %s, %s, %s
           WHERE NOT EXISTS (SELECT 1 FROM quality_inspections WHERE production_order_id = %s)""",
        [(po_ids[po], insp, aware(ts), n, rej, res, po_ids[po])
         for po, insp, ts, n, rej, res in data["inspections"]])

    cur.executemany(
        """INSERT INTO shipments (shipment_number, sales_order_id, shipped_at,
                                  delivered_at, shipment_status, freight_cost_brl)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT (shipment_number) DO UPDATE
               SET delivered_at = EXCLUDED.delivered_at,
                   shipment_status = EXCLUDED.shipment_status
               WHERE shipments.shipment_status IS DISTINCT FROM EXCLUDED.shipment_status""",
        [(sh, so_ids[so], aware(s), aware(d), st, freight)
         for sh, so, s, d, st, freight in data["shipments"]])

    return {k: len(v) for k, v in data.items()}
