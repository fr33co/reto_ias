"""NON-functional measurement: p95 with 60,000 dispatches and 400 per cycle. Run with `make perf`."""
import statistics
import time

import pytest
from sqlalchemy import text

from .conftest import body

pytestmark = pytest.mark.perf
N_PLOTS, PER_PLOT = 150, 400   # 60,000 dispatches


def p95(xs):
    """95th percentile of a list of milliseconds."""
    return statistics.quantiles(xs, n=100)[94]


def test_p95_post_and_get_with_60000_dispatches(app, client, auth):
    """Seed 60,000 dispatches (400 per plot) and assert GET p95 <= 200 ms and POST p95 <= 300 ms."""
    e = app.extensions["engine"]
    with e.begin() as c:
        c.execute(text("""INSERT INTO plots SELECT 'S-' || (500 + g), 'SUR', 130, 120, DATE '2026-09-14', 'CORTE', 'FERTIRRIEGO'
                          FROM generate_series(0, :n - 1) g"""), {"n": N_PLOTS})
        c.execute(text("""
            INSERT INTO dispatches
            SELECT gen_random_uuid(), 'OF-' || (3000 + s) || '-' || lpad(d::text, 4, '0'), 'S-' || (500 + s), 'URE', 1.0, 1, 50, 23000,
                   'x', '0001', 'SUR-1', 'B-SUR-01', TIMESTAMPTZ '2026-09-15 06:30-05' + d * interval '10 minutes',
                   DATE '2026-09-15' + (d / 6)
            FROM generate_series(0, :n - 1) s, generate_series(0, :m - 1) d"""), {"n": N_PLOTS, "m": PER_PLOT})
        c.execute(text("ANALYZE dispatches"))
        assert c.execute(text("SELECT count(*) FROM dispatches")).scalar_one() >= 60000

    h = auth("B-SUR-01")
    get_ms, post_ms = [], []
    for i in range(300):
        t = time.perf_counter()
        r = client.get(f"/api/v1/suertes/S-{500 + i % N_PLOTS}/balance-nitrogeno", headers=h)
        get_ms.append((time.perf_counter() - t) * 1000)
        assert r.status_code == 200 and r.json["historial"]["paginas"] == 8
    for i in range(300):
        t = time.perf_counter()
        r = client.post(f"/api/v1/suertes/S-{500 + i % N_PLOTS}/despachos",
                        json=body(f"OF-2027-{i:04d}", "URE", 0.2, "1113990457"), headers=h)
        post_ms.append((time.perf_counter() - t) * 1000)
        assert r.status_code == 201, r.json
    print(f"\nGET  p95={p95(get_ms):.1f} ms (target 200)   POST p95={p95(post_ms):.1f} ms (target 300)")
    assert p95(get_ms) <= 200 and p95(post_ms) <= 300
