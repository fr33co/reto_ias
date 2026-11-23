"""Immutable domain objects. They carry no persistence or HTTP concerns."""
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class OperatorSession:
    """The authenticated operator, taken from the verified token.

    Attributes:
        id: Operator id (e.g. `B-SUR-01`).
        warehouse: Warehouse the operator may use (`NORTE` or `SUR`).
        counter: Service window (e.g. `SUR-1`).
    """
    id: str            # B-SUR-01
    warehouse: str     # SUR
    counter: str       # SUR-1 (the service window)


@dataclass(frozen=True)
class Plot:
    """A crop plot (*suerte*).

    Attributes:
        code: `S-NNN`.
        warehouse: Owning warehouse.
        net_area_dha: Net area in tenths of a hectare (42.5 ha -> 425).
        cycle_start: First day of the current crop cycle.
    """
    code: str
    warehouse: str
    net_area_dha: int
    cycle_start: date


@dataclass(frozen=True)
class Dispatch:
    """A registered dispatch (immutable, append-only).

    Attributes:
        order: Fertilization order number.
        dose_dkg_ha: Dose in tenths of kg/ha of the main nutrient.
        bags: Closed bags loaded.
        delivered_kg: `bags * bag_kg`.
        n_grams: Nitrogen delivered, in grams (exact integer).
        foreman_last4: Last four digits of the foreman's id (the full id is stored encrypted).
        counter, registered_by, registered_at: Where, who and when.
        net_area_dha: Plot net area, only used to present N per hectare.
    """
    id: str
    order: str
    plot: str
    product: str
    dose_dkg_ha: int
    bags: int
    delivered_kg: int
    n_grams: int
    foreman_last4: str
    counter: str
    registered_by: str
    registered_at: datetime
    net_area_dha: int = 0   # only used to present n per hectare


@dataclass(frozen=True)
class DispatchRequest:
    """A validated request to register a dispatch.

    Attributes:
        dose_dkg_ha: Dose in tenths of kg/ha.
        national_id: The foreman's full id (never logged or returned).
        confirmed_bags: Bags the counter confirmed on screen (must match the computed ones).
    """
    order: str
    product: str
    dose_dkg_ha: int
    national_id: str
    confirmed_bags: int | None = None


@dataclass(frozen=True)
class Balance:
    """A plot's nitrogen balance.

    Attributes:
        cycle_n_g: Nitrogen delivered in the cycle, in grams.
        page, pages: Current history page and page count.
        dispatches: The rows of the current page, newest first.
    """
    plot: Plot
    cycle_n_g: int
    page: int
    pages: int
    dispatches: list[Dispatch]
