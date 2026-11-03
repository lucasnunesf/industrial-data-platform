# Simulation assumptions

The production flow is based on the real operation of AC Metais. All numbers below are assumptions used to generate synthetic data; they live in `simulator/factory_config.py` (parameters) and `erp/seed.sql` (fixed factory layout).

## Factory layout

| Work center | Code | Machines | Operators |
|---|---|---|---|
| Laser cutting | CUT | 2 laser cutters (LSR-01, LSR-02) | 2 machine operators, 2 unloaders |
| Laser welding | WELD | 1 laser welder (WLD-01) | welders from fabrication |
| Fabrication (manual welding and assembly) | FAB | none (workbenches) | 5 welders, 5 assemblers |
| Finishing | FIN | none | 5 finishers |
| Quality control | QC | none | 1 inspector |

## Routings

| Routing | Steps | Share of products |
|---|---|---|
| CUT_ONLY | CUT | 40% |
| CUT_FAB | CUT → FAB → FIN | 35% |
| FULL | CUT → WELD → FAB → FIN | 25% |

## Operation

- One shift, Monday to Friday, 07:00–16:00 (America/Sao_Paulo); all timestamps are stored in UTC.
- Simulation starts on 2026-07-01 with 40 customers ("Company 001"…) and 30 products.
- 2–6 sales orders per working day, 1–4 lines per order, 5–40 units per line.
- Customers are promised delivery 7–30 days after the order.
- Processing time per stage = setup + units × minutes per unit, scaled by part weight, with random variation.
- Parallel capacity: CUT 2, WELD 1, FAB 10, FIN 5 jobs at a time.
- Scrap rates: CUT 3%, WELD 1%, FAB 1.5%, FIN 0.5%.
- Quality inspects about 20% of production orders by sampling 20% of the units.
- Material prices (BRL/kg): carbon steel 9, stainless steel 32, aluminum 38.

## Design choices

- Shop-floor execution is stored as append-only `start`/`finish` events (`production_stage_events`), like a real MES.
- Headers that change over time (`sales_orders`, `production_orders`, `shipments`) are updated in place, and a trigger keeps `updated_at` current for incremental extraction.
- The simulator is deterministic (fixed seed): re-running with a later cut-off reproduces the same past and only adds new history.
