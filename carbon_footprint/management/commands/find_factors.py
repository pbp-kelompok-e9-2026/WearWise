import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

BASE = "https://api.climatiq.io/data/v1"


class Command(BaseCommand):
    help = "Cari emission factor Climatiq. Contoh: python manage.py find_factors cotton"

    def add_arguments(self, parser):
        parser.add_argument("query")
        parser.add_argument("--unit-type", default="Weight")
        parser.add_argument("--source", default="")
        parser.add_argument("--region", default="")
        parser.add_argument("--year", default="")
        parser.add_argument("--limit", type=int, default=20)

    def handle(self, *args, **opts):
        headers = {"Authorization": f"Bearer {settings.CLIMATIQ_API_KEY}"}
        try:
            v = requests.get(f"{BASE}/data-versions", headers=headers, timeout=10)
            v.raise_for_status()
            data_version = "^" + v.json()["latest_release"]

            params = {"query": opts["query"], "data_version": data_version,
                      "results_per_page": opts["limit"], "access_type": "public"}
            for key in ("unit_type", "source", "region", "year"):
                if opts[key]:
                    params[key] = opts[key]
            resp = requests.get(f"{BASE}/search", headers=headers, params=params, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise CommandError(f"Gagal memanggil Climatiq: {exc}")

        data = resp.json()
        self.stdout.write(f"data_version: {data_version} | total hasil: {data.get('total_results')}\n")
        for r in data["results"]:
            self.stdout.write(
                f"{r['id']} | {r['name']} | {r.get('source')} {r.get('year')} | {r.get('region')} | "
                f"{r.get('unit_type')} ({r.get('unit')}) | tahap: {r.get('source_lca_activity')} | faktor: {r.get('factor')}"
            )
        self.stdout.write(f"\nfilter tersedia: {data.get('possible_filters')}")