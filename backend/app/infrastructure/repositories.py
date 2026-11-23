"""SQLAlchemy implementations of the application ports (repositories and unit of work)."""
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..domain.errors import DuplicateOrder
from ..domain.models import Dispatch, Plot
from .orm import DispatchORM, PlotORM

BOGOTA = ZoneInfo("America/Bogota")


def _tenths(v: Decimal) -> int:
    """Convert a `Decimal` with one decimal place (e.g. 42.5) to integer tenths (425)."""
    return int(v * 10)


class SqlPlotRepository:
    """`PlotRepository` implemented with SQLAlchemy."""

    def __init__(self, s: Session):
        """Initialise the instance.

        Args:
            s: The ORM session of the current unit of work.
        """
        self._s = s

    def get(self, code: str, lock: bool = False) -> Plot | None:
        """See `PlotRepository.get`. With `lock=True` issues `SELECT ... FOR UPDATE`."""
        q = select(PlotORM).where(PlotORM.code == code)
        if lock:
            q = q.with_for_update()          # SELECT ... FOR UPDATE
        row = self._s.execute(q).scalar_one_or_none()
        return Plot(row.code, row.warehouse, _tenths(row.net_area_ha), row.cycle_start) if row else None


class SqlDispatchRepository:
    """`DispatchRepository` implemented with SQLAlchemy."""

    def __init__(self, s: Session):
        """Initialise the instance.

        Args:
            s: The ORM session of the current unit of work.
        """
        self._s = s

    @staticmethod
    def _in_cycle(plot: str, since: date):
        """SQL conditions selecting the dispatches of a plot's cycle (`local_date >= since`)."""
        return (DispatchORM.plot == plot, DispatchORM.local_date >= since)

    def order_exists(self, order: str) -> bool:
        """See `DispatchRepository.order_exists`."""
        return self._s.execute(select(DispatchORM.id).where(DispatchORM.order_no == order)).first() is not None

    def cycle_nitrogen_g(self, plot: str, since: date) -> int:
        """Sum `n_grams` over the whole cycle, served by the covering index."""
        q = select(func.coalesce(func.sum(DispatchORM.n_grams), 0)).where(*self._in_cycle(plot, since))
        return int(self._s.execute(q).scalar_one())

    def count_cycle(self, plot: str, since: date) -> int:
        """Count the dispatches of the cycle."""
        q = select(func.count()).select_from(DispatchORM).where(*self._in_cycle(plot, since))
        return self._s.execute(q).scalar_one()

    def cycle_page(self, plot, since, limit, offset, net_area_dha) -> list[Dispatch]:
        """History page ordered `local_date DESC, registered_at DESC, id` (the id breaks ties so pages are stable)."""
        q = (select(DispatchORM).where(*self._in_cycle(plot, since))
             .order_by(DispatchORM.local_date.desc(), DispatchORM.registered_at.desc(), DispatchORM.id)
             .limit(limit).offset(offset))
        return [Dispatch(str(r.id), r.order_no, r.plot, r.product, _tenths(r.dose_kg_ha), r.bags,
                         r.delivered_kg, r.n_grams, r.foreman_last4.strip(), r.counter, r.registered_by,
                         r.registered_at.astimezone(BOGOTA), net_area_dha)
                for r in self._s.execute(q).scalars()]

    def add(self, d: Dispatch, encrypted_national_id: str) -> None:
        """Insert the dispatch inside a SAVEPOINT.

        The SAVEPOINT lets a duplicate-order violation be translated into `DuplicateOrder`
        without invalidating the outer transaction.

        Raises:
            DuplicateOrder: A concurrent request already used the order number.
        """
        row = DispatchORM(
            id=UUID(d.id), order_no=d.order, plot=d.plot, product=d.product,
            dose_kg_ha=Decimal(d.dose_dkg_ha) / 10, bags=d.bags, delivered_kg=d.delivered_kg,
            n_grams=d.n_grams, foreman_encrypted_id=encrypted_national_id, foreman_last4=d.foreman_last4,
            counter=d.counter, registered_by=d.registered_by, registered_at=d.registered_at,
            local_date=d.registered_at.astimezone(BOGOTA).date())
        try:
            with self._s.begin_nested():
                self._s.add(row)
        except IntegrityError as e:  # same order on another plot, racing another counter
            if "order_no" in str(e.orig):
                raise DuplicateOrder() from e
            raise


class _UnitOfWork:
    """Groups the repositories that share one ORM session (one transaction)."""

    def __init__(self, s: Session):
        """Initialise the instance.

        Args:
            s: The ORM session shared by both repositories.
        """
        self.plots = SqlPlotRepository(s)
        self.dispatches = SqlDispatchRepository(s)


def uow_factory(engine: Engine):
    """Build the unit-of-work factory.

    Reads use a REPEATABLE READ read-only snapshot (sum, count and page agree); writes use
    READ COMMITTED and rely on the plot's row lock.

    Args:
        engine: The engine.

    Returns:
        A callable returning a context manager that commits on success and rolls back on error.
    """
    read_engine = engine.execution_options(isolation_level="REPEATABLE READ", postgresql_readonly=True)

    @contextmanager
    def uow(read_only: bool = False):
        """Open a transaction and yield its unit of work.

        Args:
            read_only: Use the read-only snapshot engine.
        """
        # Read: one snapshot (sum and page agree). Write: READ COMMITTED + FOR UPDATE on the plot.
        with Session(read_engine if read_only else engine, expire_on_commit=False) as s, s.begin():
            yield _UnitOfWork(s)
    return uow
