# Power BI dashboard

Source: the six tables of the `gold` schema in the Fabric Warehouse `wh_industrial`, loaded in Import mode through the SQL Server connector (sign in with an organizational account). The measures are in [measures.dax](measures.dax).

The report pages are generated as code: the report is saved as a Power BI Project (`.pbip`, PBIR format) and [build_report.py](build_report.py) writes every visual and the theme:

```bash
python powerbi/build_report.py "<path>/<name>.Report"
```

## Design

- Each page answers one question with four KPI cards, three charts and one table.
- Navy and orange on a light background. The most critical KPI of each page is orange.
- In "Wait by stage", the stage with the longest wait is orange (measure `Wait Color`), so the highlight follows the filters.
- Short titles, sorted bars with data labels.

## Relationships (many to one, single direction)

| From | To |
|---|---|
| `fct_stage_execution[work_center_id]` | `dim_work_center[work_center_id]` |
| `fct_stage_execution[machine_id]` | `dim_machine[machine_id]` |
| `fct_stage_execution[product_id]` | `dim_product[product_id]` |
| `fct_stage_execution[customer_id]` | `dim_customer[customer_id]` |
| `fct_order_delivery[customer_id]` | `dim_customer[customer_id]` |

There is no relationship between `dim_machine` and `dim_work_center`: it would create a second path from `fct_stage_execution` to the work center.

## Page 1 — Production bottlenecks

| Visual | Content |
|---|---|
| KPI cards | Wait (h), Duration (h), Scrap, Stage runs |
| Bar chart | Wait by stage (h), bottleneck in orange |
| Column chart | Duration by stage (h) |
| Column chart | Scrap by stage |
| Table | Products by wait, with routing, scrap and stage runs |
| Slicers | Customer, Material |

## Page 2 — On-time delivery

| Visual | Content |
|---|---|
| KPI cards | On time, Late orders, Days late, Lead time (days) |
| Column chart | On time vs late by order month |
| Donut | On time vs late |
| Bar chart | Top 10 late customers |
| Table | Late orders, most delayed first |
| Slicers | State, Status |

## Reading the numbers

- Wait and duration are wall-clock times and include nights and weekends (ADR-006). They compare stages; they are not machine time.
- Laser cutting is the first stage of every routing, so it has no wait.
- On time only counts delivered orders; open orders have no `is_on_time`.

## Page 3: Order margin

Source: `fct_order_margin` (one row per shipped sales order), related to `dim_customer` by `customer_id`.

- Cards: Margin %, Revenue, Material cost, Freight cost.
- Margin % by month of the order date.
- Donut: how revenue splits into material, processing, freight and margin.
- Freight as a share of revenue by customer state.
- Table of orders with revenue, margin and margin %.

Margin = revenue − material − processing − freight. It leaves out taxes, overhead and rework.
