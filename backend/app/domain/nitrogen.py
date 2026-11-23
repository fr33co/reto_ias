"""Pure nitrogen-balance arithmetic.

Everything is computed with INTEGERS so the limit is decided without rounding error:
  - net area and dose in tenths (42.5 ha -> 425; 80.0 kg/ha -> 800)
  - nitrogen in grams
Decimal only appears when presenting kg/ha.
"""
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from .catalog import LIMIT_N_KG_HA, Product

_HUNDREDTH = Decimal("0.01")


def bags_for_dose(dose_dkg_ha: int, net_area_dha: int, product: Product) -> int:
    """Nearest CLOSED bag count (half rounds up) that satisfies the dose.

    main_kg = dose * area ; product_kg = main_kg * 100 / pct ; bags = product_kg / bag_kg.
    In tenths: bags = dose_d * area_d / (pct * bag_kg).
    """
    num = dose_dkg_ha * net_area_dha
    den = product.main_pct * product.bag_kg
    return (2 * num + den) // (2 * den)


def n_grams(bags: int, product: Product) -> int:
    """Nitrogen contained in `bags` bags of `product`, in grams (exact integer).

    `bags * bag_kg * n_pct / 100` kilograms, times 1000 grams.
    """
    return bags * product.bag_kg * product.n_pct * 10


def limit_grams(net_area_dha: int, limit_kg_ha: int = LIMIT_N_KG_HA) -> int:
    """Nitrogen limit of a plot in grams (`limit_kg_ha * hectares * 1000`).

    Args:
        net_area_dha: Net area in tenths of a hectare.
        limit_kg_ha: Limit in kg N per net hectare (default 160).
    """
    return limit_kg_ha * net_area_dha * 100


def fits_limit(cycle_n_g: int, dispatch_n_g: int, limit_g: int) -> bool:
    """A nitrogen-free dispatch (e.g. KCL) cannot 'make the cycle exceed' the limit."""
    return dispatch_n_g == 0 or cycle_n_g + dispatch_n_g <= limit_g


def max_bags(remaining_g: int, product: Product) -> int | None:
    """Largest number of bags of `product` that fit in the remaining nitrogen.

    Args:
        remaining_g: Remaining nitrogen in grams (may be negative).
        product: The product.

    Returns:
        The bag count (0 if none fits), or `None` if the product contains no nitrogen.
    """
    per_bag = product.bag_kg * product.n_pct * 10
    if per_bag == 0:
        return None
    return max(0, remaining_g // per_bag)


def to_kg_ha(grams: int, net_area_dha: int, rounding=ROUND_HALF_UP) -> Decimal:
    """Convert grams of nitrogen to kg per net hectare, rounded to 2 decimals.

    Only for presentation: limit decisions use integer grams.

    Args:
        grams: Nitrogen in grams.
        net_area_dha: Net area in tenths of a hectare.
        rounding: `decimal` rounding mode (default half-up).
    """
    return (Decimal(grams) / Decimal(net_area_dha * 100)).quantize(_HUNDREDTH, rounding=rounding)


def available_kg_ha(cycle_n_g: int, net_area_dha: int) -> Decimal:
    """Rounded DOWN so we never promise more than is really available. Minimum 0."""
    remaining = max(0, limit_grams(net_area_dha) - cycle_n_g)
    return to_kg_ha(remaining, net_area_dha, ROUND_FLOOR)
