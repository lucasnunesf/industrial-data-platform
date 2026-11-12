import argparse
from datetime import datetime

import masters
import production
from db import connect


def main() -> None:
    parser = argparse.ArgumentParser(description="AC Metais ERP simulator")
    parser.add_argument("--until", help="cut-off in local time, e.g. '2026-11-03 12:00' (default: now)")
    args = parser.parse_args()
    until = (datetime.fromisoformat(args.until) if args.until
             else datetime.now(production.TZ).replace(tzinfo=None))

    with connect() as conn:
        masters.load_all(conn, until.date())
        ctx = production.load_context(conn)
        counts = production.write(conn, production.simulate(ctx, until))

    print(f"Simulated until {until:%Y-%m-%d %H:%M}")
    for name, n in counts.items():
        print(f"  {name:<12} {n:>6}")


if __name__ == "__main__":
    main()
