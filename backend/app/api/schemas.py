"""Wire format -> domain request. Field names are the API contract (Spanish, fixed by the brief).

Mirrors the client rules in frontend/src/domain/validation.ts.
"""
import re
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

from ..domain.catalog import MAX_DOSE_KG_HA, PRODUCTS
from ..domain.errors import FieldError, InvalidData
from ..domain.models import DispatchRequest

_ORDER = re.compile(r"OF-\d{4}-\d{4}")
_NATIONAL_ID = re.compile(r"\d{6,10}")
_FIELDS = {"orden", "producto", "dosis_kg_ha", "cedula_capataz", "bultos_confirmados"}


def parse_dispatch_request(data: object) -> DispatchRequest:
    """Validate the POST body and convert it to a `DispatchRequest`.

    All problems are collected so the client can fix every field at once. Rules are the
    same as the client's (`frontend/src/domain/validation.ts`):

    - `orden`: `OF-AAAA-NNNN`; `producto`: one of the catalog;
    - `dosis_kg_ha`: a JSON number, `0 < d <= 200`, one decimal at most;
    - `cedula_capataz`: a *string* of 6 to 10 digits (a number would lose leading zeros);
    - `bultos_confirmados`: optional positive integer;
    - no other fields are accepted.

    Args:
        data: The parsed JSON body (floats already parsed as `Decimal`).

    Returns:
        The validated request, with the dose converted to tenths of kg/ha.

    Raises:
        InvalidData: With one `FieldError` per wrong field. Messages never repeat the values.
    """
    if not isinstance(data, Mapping):
        raise InvalidData([FieldError("_general", "body_object")])
    errors: list[FieldError] = []
    for extra in sorted(set(data) - _FIELDS):
        errors.append(FieldError(str(extra)[:40], "field_not_allowed"))

    order = data.get("orden")
    if not isinstance(order, str) or not _ORDER.fullmatch(order.strip()):
        errors.append(FieldError("orden", "order_format"))

    product = data.get("producto")
    if not isinstance(product, str) or product not in PRODUCTS:
        errors.append(FieldError("producto", "product_choice", {"options": ", ".join(PRODUCTS)}))

    dose_d = None
    dose = data.get("dosis_kg_ha")
    if isinstance(dose, bool) or not isinstance(dose, (int, Decimal)):
        errors.append(FieldError("dosis_kg_ha", "dose_number"))
    else:
        try:
            d = Decimal(dose)
            if not d.is_finite() or d <= 0 or d > MAX_DOSE_KG_HA:
                errors.append(FieldError("dosis_kg_ha", "dose_range", {"max": MAX_DOSE_KG_HA}))
            elif d * 10 != (d * 10).to_integral_value():
                errors.append(FieldError("dosis_kg_ha", "dose_decimals"))
            else:
                dose_d = int(d * 10)
        except InvalidOperation:
            errors.append(FieldError("dosis_kg_ha", "dose_number"))

    national_id = data.get("cedula_capataz")
    if not isinstance(national_id, str) or not _NATIONAL_ID.fullmatch(national_id.strip()):
        errors.append(FieldError("cedula_capataz", "id_format"))

    confirmed = data.get("bultos_confirmados")
    if confirmed is not None and (isinstance(confirmed, bool) or not isinstance(confirmed, int) or confirmed < 1):
        errors.append(FieldError("bultos_confirmados", "confirmed_bags_int"))

    if errors:
        raise InvalidData(errors)
    return DispatchRequest(order.strip(), product, dose_d, national_id.strip(), confirmed)
