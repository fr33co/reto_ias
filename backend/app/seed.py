"""Example data from the brief (section 4.1). S-208's 104 dispatches go at 06:30 and 14:30."""
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from .domain.catalog import PRODUCTS
from .infrastructure.orm import DispatchORM, PlotORM
from .infrastructure.repositories import BOGOTA

PLOTS = [  # code, warehouse, gross, net, cycle start, origin, irrigation
    ("S-104", "NORTE", "46.8", "42.5", date(2026, 8, 21), "CORTE", "SURCOS"),
    ("S-117", "NORTE", "38.0", "35.2", date(2026, 6, 30), "CORTE", "SURCOS"),
    ("S-208", "SUR", "52.4", "48.6", date(2026, 9, 14), "CORTE", "FERTIRRIEGO"),
    ("S-212", "SUR", "29.9", "27.4", date(2025, 12, 3), "CORTE", "SURCOS"),
    ("S-221", "SUR", "18.2", "16.0", date(2026, 7, 10), "SIEMBRA", "SURCOS"),
    ("S-305", "SUR", "61.0", "56.3", date(2026, 9, 14), "CORTE", "FERTIRRIEGO"),
]
PRIOR = [  # date, plot, product, bags
    (date(2026, 6, 15), "S-104", "URE", 60), (date(2026, 9, 10), "S-104", "URE", 85),
    (date(2026, 10, 20), "S-104", "DAP", 92), (date(2026, 8, 2), "S-117", "SAM", 120),
    (date(2026, 9, 15), "S-117", "URE", 110), (date(2026, 2, 10), "S-212", "URE", 70),
    (date(2026, 5, 20), "S-212", "SAM", 150), (date(2026, 8, 5), "S-221", "URE", 83),
    (date(2026, 8, 5), "S-221", "SAM", 16),
]
_COUNTER = {"NORTE": ("B-NORTE-01", "NORTE-1"), "SUR": ("B-SUR-01", "SUR-1")}


def _prior_rows():
    """Build the brief's pre-existing dispatches (section 4.1): the 9 listed rows plus S-208's 104 two-bag urea dispatches at 06:30 and 14:30 from 2026-10-02 to 2026-11-22.

    Returns:
        A list of `(timestamp, plot, product, bags)`.
    """
    rows = [(datetime.combine(d, datetime.min.time()).replace(hour=8, tzinfo=BOGOTA), p, prod, bags)
            for d, p, prod, bags in PRIOR]
    day = date(2026, 10, 2)
    while day <= date(2026, 11, 22):
        for h, m in ((6, 30), (14, 30)):
            rows.append((datetime(day.year, day.month, day.day, h, m, tzinfo=BOGOTA), "S-208", "URE", 2))
        day += timedelta(days=1)
    return rows


def seed_example_data(engine: Engine, encryptor) -> None:
    """Idempotent: never duplicates plots or orders already loaded."""
    areas = {p[0]: Decimal(p[3]) for p in PLOTS}
    warehouses = {p[0]: p[1] for p in PLOTS}
    national_id = encryptor.encrypt("1000000001")   # synthetic id
    with Session(engine) as ses, ses.begin():
        for code, warehouse, gross, net, start, origin, irrigation in PLOTS:
            if ses.get(PlotORM, code) is None:
                ses.add(PlotORM(code=code, warehouse=warehouse, gross_area_ha=Decimal(gross),
                                net_area_ha=Decimal(net), cycle_start=start, cycle_origin=origin,
                                irrigation=irrigation))
        ses.flush()
        existing = set(ses.scalars(select(DispatchORM.order_no)))
        for i, (at, plot, code, bags) in enumerate(_prior_rows(), start=1):
            order = f"OF-2026-{i:04d}"
            if order in existing:
                continue
            p = PRODUCTS[code]
            dose = (Decimal(bags * p.bag_kg * p.main_pct) / 100 / areas[plot]).quantize(Decimal("0.1"))
            by, counter = _COUNTER[warehouses[plot]]
            ses.add(DispatchORM(
                id=uuid.uuid4(), order_no=order, plot=plot, product=code,
                dose_kg_ha=min(max(dose, Decimal("0.1")), Decimal("200")), bags=bags,
                delivered_kg=bags * p.bag_kg, n_grams=bags * p.bag_kg * p.n_pct * 10,
                foreman_encrypted_id=national_id, foreman_last4="0001", counter=counter,
                registered_by=by, registered_at=at, local_date=at.date()))
