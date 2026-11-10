# Power BI dashboard

Source: the six tables of the `gold` schema in the Fabric Warehouse `wh_industrial`, loaded in Import mode through the SQL Server connector (sign in with an organizational account). The measures are in [measures.dax](measures.dax).

Each page answers one business question: four KPI cards, three charts and one detail table. Chart titles are the question they answer, bars are sorted and show data labels, and the palette is navy, blue and white.

## Relationships (many to one, single direction)

| From | To |
|---|---|
| `fct_stage_execution[work_center_id]` | `dim_work_center[work_center_id]` |
| `fct_stage_execution[machine_id]` | `dim_machine[machine_id]` |
| `fct_stage_execution[product_id]` | `dim_product[product_id]` |
| `fct_stage_execution[customer_id]` | `dim_customer[customer_id]` |
| `fct_order_delivery[customer_id]` | `dim_customer[customer_id]` |

There is no relationship between `dim_machine` and `dim_work_center`: it would create a second path from `fct_stage_execution` to the work center.

## Page 1 — Where is the bottleneck?

| Visual | Content |
|---|---|
| KPI cards | `Avg Wait (h)`, `Avg Duration (h)`, `Scrap %`, `Stage Runs` |
| Bar chart | Average wait before each stage (h), by work center |
| Column chart | Average duration of each stage (h), by work center |
| Column chart | Scrap rate by work center |
| Table | Products ranked by average wait, with routing, scrap and runs |
| Slicers | Customer, material |

## Page 2 — Are we delivering on time?

| Visual | Content |
|---|---|
| KPI cards | `On-Time %`, `Late Orders`, `Avg Days Late (late orders)`, `Avg Lead Time (days)` |
| Line chart | `On-Time %` by order month |
| Donut | Delivered orders on time vs late |
| Bar chart | Top 10 customers by late orders |
| Table | Late orders only, most delayed first |
| Slicers | Customer state, order status |

## Reading the numbers

- Wait and duration are wall-clock times and include nights and weekends (ADR-006). They compare stages; they are not machine time.
- Laser cutting is the first stage of every routing, so it has no wait.
- `On-Time %` only counts delivered orders; open orders have no `is_on_time`.
