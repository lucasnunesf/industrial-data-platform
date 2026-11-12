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
- Scrap propagates: each stage receives only the good output of the previous one, and its processing time is based on those units.
- Quality inspects about 20% of production orders by sampling 20% of the units.
- Sales price list (BRL/kg of material, used to price each product): carbon steel 9, stainless steel 32, aluminum 38.

## Finance and logistics

All prices and rates in this section are invented for the simulation. Only the exchange rate is real.

- Material is bought in US dollars per kg: carbon steel 1.70, stainless steel 6.00, aluminum 7.20.
- The USD/BRL rate is the real PTAX published by Banco Central do Brasil, downloaded once to `simulator/data/ptax_usd_brl.csv` (`simulator/download_ptax.py`). PTAX exists for business days only; a day without a rate uses the latest previous one.
- The sales price list is fixed in BRL, so the margin moves with the exchange rate.
- Hourly rate per work center (BRL): laser cutting 180, laser welding 150, fabrication 70, finishing 55, quality control 60.
- Each `finish` event reports `work_minutes`, the working time spent on the stage. Unlike the difference between the start and finish timestamps, it has no nights or weekends.
- Freight per shipment = order weight × rate per kg, with a minimum of BRL 120. Rates (BRL/kg): 0.35 inside São Paulo state, 0.60 to the other South and Southeast states, 1.10 elsewhere. The plant is in Sorocaba, SP.
- Margin here means revenue minus material, machine and labor time at the work centers, and freight. It leaves out taxes, overhead and rework.

## Design choices

- Shop-floor execution is stored as append-only `start`/`finish` events (`production_stage_events`), like a real MES.
- Headers that change over time (`sales_orders`, `production_orders`, `shipments`) are updated in place, and a trigger keeps `updated_at` current for incremental extraction.
- The simulator is deterministic (fixed seed): re-running with a later cut-off reproduces the same past and only adds new history.
