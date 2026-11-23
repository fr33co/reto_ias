"""Ports (DIP): use cases depend on these interfaces, never on SQL or Fernet."""
from contextlib import AbstractContextManager
from datetime import date, datetime
from typing import Protocol

from ..domain.models import Dispatch, Plot


class PlotRepository(Protocol):
    """Read access to plots."""

    def get(self, code: str, lock: bool = False) -> Plot | None:
        """Fetch a plot by code.

        Args:
            code: Plot code (`S-NNN`).
            lock: When true, take a row lock (`SELECT ... FOR UPDATE`) held until the
                transaction ends, serialising writers on the same plot.

        Returns:
            The plot, or `None` if it does not exist.
        """
        ...


class DispatchRepository(Protocol):
    """Access to dispatches (append-only)."""

    def order_exists(self, order: str) -> bool:
        """Return whether a dispatch already exists for this fertilization order."""
        ...

    def cycle_nitrogen_g(self, plot: str, since: date) -> int:
        """Total nitrogen (grams) delivered to the plot in its current cycle.

        Must be computed by aggregation over the *whole* cycle, never from a paginated list.

        Args:
            plot: Plot code.
            since: First day of the cycle (inclusive, America/Bogota date).
        """
        ...

    def count_cycle(self, plot: str, since: date) -> int:
        """Number of dispatches in the cycle (used to compute the page count)."""
        ...

    def cycle_page(self, plot: str, since: date, limit: int, offset: int, net_area_dha: int) -> list[Dispatch]:
        """One page of the cycle's history, newest first.

        Args:
            plot: Plot code.
            since: First day of the cycle.
            limit: Page size.
            offset: Rows to skip.
            net_area_dha: Net area in tenths of a hectare (to present N per hectare).
        """
        ...

    def add(self, d: Dispatch, encrypted_national_id: str) -> None:
        """Persist a new dispatch.

        Args:
            d: The dispatch.
            encrypted_national_id: The foreman's full id, already encrypted.

        Raises:
            DuplicateOrder: If the order number is already used.
        """
        ...


class UnitOfWork(Protocol):
    """One transaction exposing the repositories it uses."""

    plots: PlotRepository
    dispatches: DispatchRepository


class UnitOfWorkFactory(Protocol):
    """Creates units of work as context managers (commit on exit, rollback on error)."""

    def __call__(self, read_only: bool = False) -> AbstractContextManager[UnitOfWork]:
        """Open a transaction.

        Args:
            read_only: When true, use a read-only consistent snapshot.
        """
        ...


class Clock(Protocol):
    """Source of the current time."""

    def now(self) -> datetime:
        """Return the current time, timezone-aware (America/Bogota)."""
        ...


class Encryptor(Protocol):
    """Reversible encryption for personal data."""

    def encrypt(self, text: str) -> str:
        """Encrypt `text` and return an opaque string safe to store."""
        ...
