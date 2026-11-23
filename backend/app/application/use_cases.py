"""Use cases: orchestrate domain + ports. No Flask, no SQL."""
import math
import uuid

from ..domain import nitrogen as nit
from ..domain.catalog import PAGE_SIZE, PRODUCTS
from ..domain.errors import (AccessDenied, DuplicateOrder, FieldError, InvalidData,
                             NitrogenLimitExceeded, PlotNotFound)
from ..domain.models import Balance, Dispatch, DispatchRequest, OperatorSession, Plot
from .ports import Clock, Encryptor, UnitOfWorkFactory


def _authorize(plot: Plot | None, session: OperatorSession) -> Plot:
    """Check that the plot exists and belongs to the session's warehouse.

    Args:
        plot: The plot or `None` if not found.
        session: The operator's session.

    Returns:
        The authorised plot.

    Raises:
        PlotNotFound: The plot does not exist.
        AccessDenied: The plot belongs to another warehouse.
    """
    if plot is None:
        raise PlotNotFound()
    if plot.warehouse != session.warehouse:
        raise AccessDenied()
    return plot


def _build_balance(uow, plot: Plot, page: int) -> Balance:
    """Build the balance of a plot for one history page.

    Cycle nitrogen comes from an aggregate query, *never* from the page rows (this is the
    fix for the v1 incident, where the paginated query fed the business rule).

    Args:
        uow: The active unit of work.
        plot: The authorised plot.
        page: 1-based history page.

    Returns:
        The balance with at least one page.
    """
    # Cycle nitrogen ALWAYS comes from an aggregate, never from the paginated history.
    cycle_n = uow.dispatches.cycle_nitrogen_g(plot.code, plot.cycle_start)
    total = uow.dispatches.count_cycle(plot.code, plot.cycle_start)
    rows = uow.dispatches.cycle_page(plot.code, plot.cycle_start, PAGE_SIZE,
                                     (page - 1) * PAGE_SIZE, plot.net_area_dha)
    return Balance(plot, cycle_n, page, max(1, math.ceil(total / PAGE_SIZE)), rows)


class GetBalance:
    """Use case: nitrogen balance and history of a plot."""

    def __init__(self, uow: UnitOfWorkFactory):
        """Initialise the instance.

        Args:
            uow: Factory of units of work.
        """
        self._uow = uow

    def execute(self, session: OperatorSession, plot_code: str, page: int = 1) -> Balance:
        """Return the balance inside a read-only, consistent snapshot.

        Args:
            session: The operator's session.
            plot_code: Plot code.
            page: 1-based history page.

        Raises:
            PlotNotFound: The plot does not exist.
            AccessDenied: The plot belongs to another warehouse.
        """
        with self._uow(read_only=True) as uow:
            plot = _authorize(uow.plots.get(plot_code), session)
            return _build_balance(uow, plot, page)


class RegisterDispatch:
    """Use case: register a dispatch only if the plot stays within the nitrogen limit."""

    def __init__(self, uow: UnitOfWorkFactory, clock: Clock, encryptor: Encryptor):
        """Initialise the instance.

        Args:
            uow: Factory of units of work.
            clock: Time source.
            encryptor: Encrypts the foreman's national id.
        """
        self._uow, self._clock, self._encryptor = uow, clock, encryptor

    def execute(self, session: OperatorSession, plot_code: str, req: DispatchRequest) -> Dispatch:
        """Validate business rules and persist the dispatch in one transaction.

        Steps: lock the plot row (so two counters cannot interleave), reject a repeated
        order, convert the dose to closed bags, compare with the confirmed bags, sum the
        cycle's nitrogen and accept only if `cycle + dispatch <= limit`.

        Args:
            session: The operator's session (warehouse, counter and id are recorded).
            plot_code: Plot code.
            req: The validated request.

        Returns:
            The registered dispatch.

        Raises:
            PlotNotFound: The plot does not exist.
            AccessDenied: The plot belongs to another warehouse.
            DuplicateOrder: The order was already dispatched.
            InvalidData: The dose is below one bag or the confirmed bags differ.
            NitrogenLimitExceeded: The dispatch would exceed the limit (carries max bags and balance).
        """
        with self._uow() as uow:
            # Row lock: serializes the counters dispatching to the SAME plot.
            plot = _authorize(uow.plots.get(plot_code, lock=True), session)
            if uow.dispatches.order_exists(req.order):
                raise DuplicateOrder()

            product = PRODUCTS[req.product]
            bags = nit.bags_for_dose(req.dose_dkg_ha, plot.net_area_dha, product)
            if bags < 1:
                raise InvalidData([FieldError("dosis_kg_ha", "dose_below_one_bag")])
            if req.confirmed_bags is not None and req.confirmed_bags != bags:
                raise InvalidData([FieldError("bultos_confirmados", "bags_mismatch",
                                              {"confirmed": req.confirmed_bags, "computed": bags})])

            dispatch_n = nit.n_grams(bags, product)
            cycle_n = uow.dispatches.cycle_nitrogen_g(plot.code, plot.cycle_start)
            limit = nit.limit_grams(plot.net_area_dha)
            if not nit.fits_limit(cycle_n, dispatch_n, limit):
                raise NitrogenLimitExceeded(dispatch_n, nit.max_bags(limit - cycle_n, product),
                                            _build_balance(uow, plot, 1))

            dispatch = Dispatch(str(uuid.uuid4()), req.order, plot.code, product.code, req.dose_dkg_ha, bags,
                                bags * product.bag_kg, dispatch_n, req.national_id[-4:], session.counter,
                                session.id, self._clock.now(), plot.net_area_dha)
            uow.dispatches.add(dispatch, self._encryptor.encrypt(req.national_id))
            return dispatch
