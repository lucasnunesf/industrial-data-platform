"""Download the official USD/BRL rate (PTAX) from Banco Central do Brasil to a CSV file.

The file is committed to the repository, so the simulation is reproducible and does not
depend on the API. Run it again only to extend the period:

    python simulator/download_ptax.py --until 2026-12-31
"""

import argparse
import csv
import json
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import factory_config as cfg

API = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo"
OUTPUT = Path(__file__).parent / "data" / "ptax_usd_brl.csv"


def fetch(start: date, end: date) -> list[dict]:
    query = urllib.parse.urlencode(
        {
            "@i": f"'{start:%m-%d-%Y}'",
            "@f": f"'{end:%m-%d-%Y}'",
            "$format": "json",
            "$select": "cotacaoCompra,cotacaoVenda,dataHoraCotacao",
        },
        quote_via=urllib.parse.quote,
        safe="@$',",
    )
    url = f"{API}(dataInicial=@i,dataFinalCotacao=@f)?{query}"
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)["value"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Download PTAX USD/BRL rates to a CSV file.")
    parser.add_argument("--until", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    # Start a few days early so the first simulated day always has a previous rate.
    start = cfg.START_DATE.replace(day=1).replace(month=cfg.START_DATE.month - 1)
    rows = fetch(start, args.until)

    OUTPUT.parent.mkdir(exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["rate_date", "buy_rate", "sell_rate"])
        for row in sorted(rows, key=lambda r: r["dataHoraCotacao"]):
            writer.writerow([row["dataHoraCotacao"][:10], row["cotacaoCompra"], row["cotacaoVenda"]])
    print(f"{len(rows)} rates from {start} to {args.until} -> {OUTPUT}")


if __name__ == "__main__":
    main()
