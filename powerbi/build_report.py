"""Generate the Power BI report pages (PBIR format) of a Power BI Project.

Usage: python powerbi/build_report.py "<path>/<name>.Report"

Save the report in Power BI Desktop as a Power BI Project (.pbip) first. The script
rewrites both pages, registers the custom theme and leaves the semantic model untouched;
the measures it uses are in measures.dax. Power BI Desktop reloads the project when the
option "Detect and reload external changes of PBIP" is enabled.
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
REPORT = ROOT / "definition"
RESOURCES = ROOT / "StaticResources" / "RegisteredResources"
THEME_NAME = "ACMetaisBlue.json"

SCHEMA_VISUAL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.14.0/schema.json"
SCHEMA_PAGE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
SCHEMA_PAGES = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json"

PAGE1 = "9c09fdeea404d80bbec3"
PAGE2 = "55281a6a74630230f723"

NAVY, BLUE, ORANGE = "#0B2545", "#1F6FB2", "#F2A93B"
SOFT, CANVAS, LINE, MUTED, WHITE = "#C9DCF0", "#EEF2F7", "#D9E2EC", "#627D98", "#FFFFFF"

THEME = {
    "name": "AC Metais Navy",
    "dataColors": [NAVY, ORANGE, BLUE, "#8DB8E8", "#486581", "#F7C873", "#334E68"],
    "background": WHITE,
    "foreground": NAVY,
    "tableAccent": NAVY,
    "visualStyles": {
        "*": {"*": {
            "background": [{"show": True, "color": {"solid": {"color": WHITE}}, "transparency": 0}],
            "border": [{"show": True, "color": {"solid": {"color": LINE}}, "radius": 14}],
            "dropShadow": [{"show": True, "color": {"solid": {"color": NAVY}}, "position": "Outer",
                            "preset": "BottomRight", "transparency": 82}],
            "title": [{"show": True, "fontColor": {"solid": {"color": NAVY}}, "fontSize": 14,
                       "fontFamily": "Segoe UI Semibold"}],
            "labels": [{"color": {"solid": {"color": NAVY}}, "fontSize": 11}],
            "categoryAxis": [{"labelColor": {"solid": {"color": MUTED}}, "fontSize": 11}],
            "valueAxis": [{"labelColor": {"solid": {"color": MUTED}}, "fontSize": 10, "gridlineStyle": "dotted"}],
            "legend": [{"labelColor": {"solid": {"color": NAVY}}, "fontSize": 11}],
        }},
        "page": {"*": {
            "background": [{"color": {"solid": {"color": CANVAS}}, "transparency": 0}],
            "outspace": [{"color": {"solid": {"color": CANVAS}}, "transparency": 0}],
        }},
        "card": {"*": {
            "background": [{"show": True, "color": {"solid": {"color": NAVY}}, "transparency": 0}],
            "border": [{"show": True, "color": {"solid": {"color": NAVY}}, "radius": 18}],
            "labels": [{"color": {"solid": {"color": WHITE}}, "fontSize": 34, "fontFamily": "Segoe UI Semibold"}],
            "categoryLabels": [{"color": {"solid": {"color": SOFT}}, "fontSize": 14}],
        }},
        "tableEx": {"*": {
            "columnHeaders": [{"backColor": {"solid": {"color": WHITE}}, "fontColor": {"solid": {"color": NAVY}},
                               "fontFamily": "Segoe UI Semibold"}],
            "values": [{"fontColorPrimary": {"solid": {"color": NAVY}}, "backColorPrimary": {"solid": {"color": WHITE}},
                        "backColorSecondary": {"solid": {"color": "#F5F8FB"}}}],
            "total": [{"fontColor": {"solid": {"color": NAVY}}}],
            "grid": [{"gridHorizontal": True, "gridHorizontalColor": {"solid": {"color": LINE}}}],
        }},
        "slicer": {"*": {
            "border": [{"show": True, "color": {"solid": {"color": LINE}}, "radius": 14}],
            "items": [{"fontColor": {"solid": {"color": NAVY}}, "textSize": 13,
                       "background": {"solid": {"color": CANVAS}}}],
            "title": [{"show": True, "fontColor": {"solid": {"color": MUTED}}, "fontSize": 11,
                       "fontFamily": "Segoe UI Semibold"}],
        }},
    },
}


def vid(label):
    return hashlib.md5(label.encode()).hexdigest()[:20]


def lit(value):
    return {"expr": {"Literal": {"Value": value}}}


def color(hex_code):
    return {"solid": {"color": lit(f"'{hex_code}'")}}


def col_field(entity, prop):
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def msr_field(entity, prop):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def column(entity, prop, display=None):
    p = {"field": col_field(entity, prop), "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}
    if display:
        p["displayName"] = display
    return p


def measure(entity, prop, display=None):
    p = {"field": msr_field(entity, prop), "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}
    if display:
        p["displayName"] = display
    return p


def month(entity, prop):
    return {
        "field": {"HierarchyLevel": {"Expression": {"Hierarchy": {"Expression": {"PropertyVariationSource": {
            "Expression": {"SourceRef": {"Entity": entity}}, "Name": "Variação", "Property": prop}},
            "Hierarchy": "Hierarquia de datas"}}, "Level": "Mês"}},
        "queryRef": f"{entity}.{prop}.Variação.Hierarquia de datas.Mês",
        "nativeQueryRef": f"{prop} Mês",
    }


def visual(label, vtype, x, y, w, h, order, roles=None, objects=None, title=None,
           container=None, sort=None, filters=None, title_align=None):
    body = {"visualType": vtype}
    if roles:
        body["query"] = {"queryState": {role: {"projections": f} for role, f in roles.items()}}
        if sort:
            body["query"]["sortDefinition"] = {"sort": [{"field": sort, "direction": "Descending"}],
                                               "isDefaultSort": False}
    if objects:
        body["objects"] = objects
    vco = dict(container or {})
    if title:
        vco["title"] = [{"properties": {"show": lit("true"), "text": lit(f"'{title}'")}}]
        if title_align:
            vco["title"][0]["properties"]["alignment"] = lit(f"'{title_align}'")
        vco["subTitle"] = [{"properties": {"show": lit("false")}}]
    if vco:
        body["visualContainerObjects"] = vco
    body["drillFilterOtherVisuals"] = True
    content = {
        "$schema": SCHEMA_VISUAL, "name": vid(label),
        "position": {"x": x, "y": y, "z": order, "height": h, "width": w, "tabOrder": order},
        "visual": body,
    }
    if filters:
        content["filterConfig"] = {"filters": filters}
    return vid(label), content


HIDE_VALUE_AXIS = [{"properties": {"show": lit("false"), "gridlineShow": lit("false")}}]


def labels_on(**extra):
    props = {"show": lit("true")}
    props.update(extra)
    return [{"properties": props}]


def solid_bars(hex_code):
    return {"dataPoint": [{"properties": {"fill": color(hex_code)}}], "labels": labels_on(),
            "valueAxis": HIDE_VALUE_AXIS}


def measure_colored_bars(entity, color_measure):
    return {"dataPoint": [{"properties": {"fill": {"solid": {"color": {"expr": msr_field(entity, color_measure)}}}},
                           "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}],
            "labels": labels_on(), "valueAxis": HIDE_VALUE_AXIS}


def table_style(widths):
    return {
        "columnHeaders": [{"properties": {"fontSize": lit("13D"), "autoSizeColumnWidth": lit("false")}}],
        "values": [{"properties": {"fontSize": lit("12D")}}],
        "columnWidth": [{"properties": {"value": lit(f"{w}D")}, "selector": {"metadata": ref}}
                        for ref, w in widths.items()],
    }


def title_block(prefix, title, subtitle):
    return [visual(f"{prefix}-title", "textbox", 20, 12, 1300, 80, 1, objects={
        "general": [{"properties": {"paragraphs": [
            {"textRuns": [{"value": title, "textStyle": {"fontSize": "30pt", "fontWeight": "bold", "color": NAVY}}],
             "horizontalTextAlignment": "center"},
            {"textRuns": [{"value": subtitle, "textStyle": {"fontSize": "11pt", "color": MUTED}}],
             "horizontalTextAlignment": "center"},
        ]}}]}, container={
        "background": [{"properties": {"show": lit("false")}}],
        "border": [{"properties": {"show": lit("false")}}],
        "dropShadow": [{"properties": {"show": lit("false")}}],
    })]


def kpis(prefix, cards):
    out = []
    for i, (entity, name, display, accent) in enumerate(cards):
        objects = {"labels": [{"properties": {"color": color(accent)}}]} if accent else None
        out.append(visual(f"{prefix}-card-{name}", "card", 20 + i * 475, 105, 455, 130, 10 + i,
                          roles={"Values": [measure(entity, name, display)]}, objects=objects))
    return out


def slicer(label, entity, prop, x, w, order, title):
    return visual(label, "slicer", x, 16, w, 76, order, title=title, title_align="center",
                  roles={"Values": [column(entity, prop)]},
                  objects={"data": [{"properties": {"mode": lit("'Dropdown'")}}],
                           "header": [{"properties": {"show": lit("false")}}],
                           "items": [{"properties": {"textSize": lit("13D"), "fontColor": color(NAVY)}}]})


S, D = "fct_stage_execution", "fct_order_delivery"
SUB = "AC Metais · synthetic data"
ROW2_Y, ROW2_H, ROW3_Y, ROW3_H = 255, 400, 675, 390

top10_customers = {
    "name": "top10latecustomers",
    "field": col_field("dim_customer", "company_name"),
    "type": "TopN",
    "filter": {
        "Version": 2,
        "From": [
            {"Name": "subquery", "Expression": {"Subquery": {"Query": {
                "Version": 2,
                "From": [{"Name": "d", "Entity": "dim_customer", "Type": 0},
                         {"Name": "f", "Entity": D, "Type": 0}],
                "Select": [{"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": "company_name"},
                            "Name": "field"}],
                "OrderBy": [{"Direction": 2, "Expression": {"Measure": {
                    "Expression": {"SourceRef": {"Source": "f"}}, "Property": "Late Orders"}}}],
                "Top": 10}}}, "Type": 2},
            {"Name": "d", "Entity": "dim_customer", "Type": 0},
        ],
        "Where": [{"Condition": {"In": {
            "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": "company_name"}}],
            "Table": {"SourceRef": {"Source": "subquery"}}}}}],
    },
}

only_late = {
    "name": "onlylateorders",
    "field": col_field(D, "is_on_time"),
    "type": "Categorical",
    "filter": {
        "Version": 2,
        "From": [{"Name": "f", "Entity": D, "Type": 0}],
        "Where": [{"Condition": {"In": {
            "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "f"}}, "Property": "is_on_time"}}],
            "Values": [[{"Literal": {"Value": "0L"}}]]}}}],
    },
}

page1 = title_block("p1", "Production bottlenecks", SUB)
page1 += [
    slicer("p1-slicer-customer", "dim_customer", "company_name", 1340, 270, 2, "Customer"),
    slicer("p1-slicer-material", "dim_product", "material_name", 1630, 270, 3, "Material"),
]
page1 += kpis("p1", [
    (S, "Avg Wait (h)", "⏱  Wait (h)", ORANGE),
    (S, "Avg Duration (h)", "⚙  Duration (h)", None),
    (S, "Scrap %", "♻  Scrap", None),
    (S, "Stage Runs", "🏭  Stage runs", None),
])
page1 += [
    visual("p1-hero-wait", "clusteredBarChart", 20, ROW2_Y, 1180, ROW2_H, 30,
           title="Wait by stage (h) · bottleneck",
           objects=measure_colored_bars(S, "Wait Color"), sort=msr_field(S, "Avg Wait (h)"), roles={
               "Category": [column("dim_work_center", "work_center_name")],
               "Y": [measure(S, "Avg Wait (h)", "Avg wait (h)")]}),
    visual("p1-duration", "clusteredColumnChart", 1220, ROW2_Y, 680, ROW2_H, 31,
           title="Duration by stage (h)",
           objects=solid_bars(NAVY), sort=msr_field(S, "Avg Duration (h)"), roles={
               "Category": [column("dim_work_center", "work_center_name")],
               "Y": [measure(S, "Avg Duration (h)", "Avg duration (h)")]}),
    visual("p1-scrap", "clusteredColumnChart", 20, ROW3_Y, 760, ROW3_H, 32,
           title="Scrap by stage",
           objects=solid_bars(ORANGE), sort=msr_field(S, "Scrap %"), roles={
               "Category": [column("dim_work_center", "work_center_name")],
               "Y": [measure(S, "Scrap %", "Scrap rate")]}),
    visual("p1-table-product", "tableEx", 800, ROW3_Y, 1100, ROW3_H, 33,
           title="Products by wait",
           sort=msr_field(S, "Avg Wait (h)"), roles={
               "Values": [column("dim_product", "product_name", "Product"),
                          column("dim_product", "routing_name", "Routing"),
                          measure(S, "Avg Wait (h)", "Avg wait (h)"), measure(S, "Scrap %", "Scrap"),
                          measure(S, "Stage Runs", "Stage runs")]},
           objects=table_style({"dim_product.product_name": 250, "dim_product.routing_name": 390,
                                f"{S}.Avg Wait (h)": 150, f"{S}.Scrap %": 120, f"{S}.Stage Runs": 140})),
]

page2 = title_block("p2", "On-time delivery", SUB)
page2 += [
    slicer("p2-slicer-state", "dim_customer", "state", 1340, 270, 2, "State"),
    slicer("p2-slicer-status", D, "sales_order_status", 1630, 270, 3, "Status"),
]
page2 += kpis("p2", [
    (D, "On-Time %", "✅  On time", None),
    (D, "Late Orders", "⚠  Late orders", ORANGE),
    (D, "Avg Days Late (late orders)", "📅  Days late", None),
    (D, "Avg Lead Time (days)", "🚚  Lead time (days)", None),
])
page2 += [
    visual("p2-hero-month", "clusteredColumnChart", 20, ROW2_Y, 1180, ROW2_H, 30,
           title="On time vs late · by month",
           objects={"labels": labels_on(), "valueAxis": HIDE_VALUE_AXIS,
                    "legend": [{"properties": {"show": lit("true"), "position": lit("'Top'")}}]},
           roles={"Category": [month(D, "order_date")],
                  "Y": [measure(D, "On-Time Orders", "On time"), measure(D, "Late Orders", "Late")]}),
    visual("p2-donut", "donutChart", 1220, ROW2_Y, 680, ROW2_H, 31,
           title="On time vs late",
           objects={"labels": labels_on(labelStyle=lit("'Category, percent of total'")),
                    "legend": [{"properties": {"show": lit("false")}}]},
           roles={"Y": [measure(D, "On-Time Orders", "On time"), measure(D, "Late Orders", "Late")]}),
    visual("p2-top-customers", "clusteredBarChart", 20, ROW3_Y, 760, ROW3_H, 32,
           title="Top 10 late customers",
           objects=solid_bars(NAVY), sort=msr_field(D, "Late Orders"), filters=[top10_customers], roles={
               "Category": [column("dim_customer", "company_name")],
               "Y": [measure(D, "Late Orders", "Late orders")]}),
    visual("p2-table-late", "tableEx", 800, ROW3_Y, 1100, ROW3_H, 33,
           title="Late orders",
           sort=col_field(D, "days_late"), filters=[only_late], roles={
               "Values": [column(D, "sales_order_number", "Order"),
                          column("dim_customer", "company_name", "Customer"),
                          column(D, "promised_date", "Promised"), column(D, "delivered_at", "Delivered"),
                          column(D, "days_late", "Days late")]},
           objects=table_style({f"{D}.sales_order_number": 170, "dim_customer.company_name": 230,
                                f"{D}.promised_date": 200, f"{D}.delivered_at": 270, f"{D}.days_late": 160})),
]


def write_page(page_id, display_name, visuals):
    page_dir = REPORT / "pages" / page_id
    vis_dir = page_dir / "visuals"
    if vis_dir.exists():
        shutil.rmtree(vis_dir)
    vis_dir.mkdir(parents=True)
    (page_dir / "page.json").write_text(json.dumps({
        "$schema": SCHEMA_PAGE, "name": page_id, "displayName": display_name,
        "displayOption": "FitToPage", "height": 1080, "width": 1920}, indent=2), encoding="utf-8")
    for name, content in visuals:
        (vis_dir / name).mkdir()
        (vis_dir / name / "visual.json").write_text(json.dumps(content, indent=2, ensure_ascii=False),
                                                    encoding="utf-8")


RESOURCES.mkdir(parents=True, exist_ok=True)
(RESOURCES / THEME_NAME).write_text(json.dumps(THEME, indent=2), encoding="utf-8")

report_file = REPORT / "report.json"
report = json.loads(report_file.read_text(encoding="utf-8"))
base = report["themeCollection"]["baseTheme"]
report["themeCollection"]["customTheme"] = {
    "name": THEME_NAME, "reportVersionAtImport": base["reportVersionAtImport"], "type": "RegisteredResources"}
packages = [p for p in report["resourcePackages"] if p["name"] != "RegisteredResources"]
packages.append({"name": "RegisteredResources", "type": "RegisteredResources", "items": [
    {"name": THEME_NAME, "path": THEME_NAME, "type": "CustomTheme"}]})
report["resourcePackages"] = packages
report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

write_page(PAGE1, "Production bottlenecks", page1)
write_page(PAGE2, "On-time delivery", page2)
(REPORT / "pages" / "pages.json").write_text(json.dumps({
    "$schema": SCHEMA_PAGES, "pageOrder": [PAGE1, PAGE2], "activePageName": PAGE1}, indent=2), encoding="utf-8")

for f in ROOT.rglob("*.json"):
    json.loads(f.read_text(encoding="utf-8"))
print("ok", sum(1 for _ in REPORT.rglob("visual.json")), "visuals")
