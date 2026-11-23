"""Integer nitrogen arithmetic and the cycle boundary (the cut day counts)."""
from datetime import date

import pytest
from sqlalchemy import text

from app.domain import nitrogen as nit
from app.domain.catalog import PRODUCTS


def test_bags_round_to_nearest_and_grams_are_exact():
    """Bags round to the nearest closed bag and nitrogen/limits are exact integer grams."""
    urea = PRODUCTS["URE"]
    assert nit.bags_for_dose(800, 425, urea) == 148          # 147.83
    assert nit.bags_for_dose(437, 274, urea) == 52           # 52.06
    assert nit.bags_for_dose(1, 10, urea) == 0               # less than half a bag
    assert nit.n_grams(148, urea) == 3_404_000
    assert nit.fits_limit(0, 0, 0) and not nit.fits_limit(0, 1, 0)
    assert nit.max_bags(1_212_000, urea) == 52 and nit.max_bags(-5, urea) == 0
    assert nit.max_bags(10, PRODUCTS["KCL"]) is None


def test_the_cut_day_counts_and_the_day_before_does_not(app, client, auth):
    """S-104's cycle starts 2026-08-21."""
    def insert(order, day):
        """Insert a dispatch for S-104 directly in the database with the given date."""
        with app.extensions["engine"].begin() as c:
            c.execute(text("""INSERT INTO dispatches VALUES (gen_random_uuid(), :o, 'S-104', 'URE', 10, 10, 500,
                230000, 'x', '0001', 'NORTE-1', 'B-NORTE-01', :d, :d)"""), {"o": order, "d": day})
    n = lambda: client.get("/api/v1/suertes/S-104/balance-nitrogeno", headers=auth("B-NORTE-01")).json["n_ciclo_kg_ha"]
    base = n()
    insert("OF-2026-2001", date(2026, 8, 20))
    assert n() == base
    insert("OF-2026-2002", date(2026, 8, 21))
    assert n() == pytest.approx(base + 5.41, abs=0.01)
