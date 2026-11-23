"""Domain objects -> JSON in the API contract's (Spanish) field names."""
from decimal import Decimal

from ..domain import nitrogen as nit
from ..domain.catalog import LIMIT_N_KG_HA, PRODUCTS
from ..domain.models import Balance, Dispatch


def _num(d: Decimal) -> float:
    """Convert a `Decimal` (already rounded to 2 decimals) to a JSON number."""
    return float(d)


def masked_foreman(last4: str) -> str:
    """Mask the foreman's national id: `xxxxxx` plus its last four digits.

    The mask has a fixed length so it does not reveal how many digits the id has.

    Args:
        last4: The last four digits.

    Returns:
        E.g. `"xxxxxx4321"`.
    """
    return "xxxxxx" + last4   # fixed length: does not reveal how many digits the id has


def dispatch_json(d: Dispatch) -> dict:
    """Serialise a dispatch with the contract's field names.

    Args:
        d: The dispatch (its `net_area_dha` must be set to present N per hectare).

    Returns:
        A JSON-ready dict. The national id is always masked.
    """
    return {
        "id": d.id, "orden": d.order, "suerte": d.plot, "producto": d.product,
        "dosis_kg_ha": d.dose_dkg_ha / 10, "bultos": d.bags, "kg_entregados": d.delivered_kg,
        "n_despacho_kg_ha": _num(nit.to_kg_ha(d.n_grams, d.net_area_dha)),
        "capataz": masked_foreman(d.foreman_last4), "ventanilla": d.counter,
        "registrado_por": d.registered_by, "registrado_en": d.registered_at.isoformat(),
    }


def balance_json(b: Balance) -> dict:
    """Serialise a balance, its product rules and the current history page.

    `n_ciclo_kg_ha` is rounded half-up and `n_disponible_kg_ha` is rounded *down* and
    never negative, so the API never promises more availability than exists.

    Args:
        b: The balance.

    Returns:
        A JSON-ready dict following the contract's `Balance`.
    """
    p = b.plot
    return {
        "suerte": p.code, "area_neta_ha": p.net_area_dha / 10, "inicio_ciclo": p.cycle_start.isoformat(),
        "limite_n_kg_ha": LIMIT_N_KG_HA,
        "n_ciclo_kg_ha": _num(nit.to_kg_ha(b.cycle_n_g, p.net_area_dha)),
        "n_disponible_kg_ha": _num(nit.available_kg_ha(b.cycle_n_g, p.net_area_dha)),
        "productos": [{"codigo": x.code, "nutriente_principal": x.main_nutrient,
                       "ley_principal": x.main_pct, "ley_n": x.n_pct, "kg_bulto": x.bag_kg}
                      for x in PRODUCTS.values()],
        "historial": {"pagina": b.page, "paginas": b.pages,
                      "despachos": [dispatch_json(d) for d in b.dispatches]},
    }
