"""Server-side translations. The language comes from Accept-Language (default: Spanish)."""
from flask import request

DEFAULT = "es"
CATALOG = {
    "es": {
        "order_format": "Use el formato OF-AAAA-NNNN, por ejemplo OF-2026-1187.",
        "product_choice": "Elija uno de: {options}.",
        "dose_number": "La dosis debe ser un número.",
        "dose_range": "La dosis debe ser mayor que 0 y hasta {max} kg/ha.",
        "dose_decimals": "La dosis admite como máximo un decimal.",
        "id_format": "La cédula debe tener de 6 a 10 dígitos.",
        "confirmed_bags_int": "Los bultos confirmados deben ser un entero positivo.",
        "field_not_allowed": "Campo no permitido.",
        "body_object": "El cuerpo debe ser un objeto JSON.",
        "content_type_json": "El contenido debe ser application/json.",
        "invalid_json": "JSON inválido.",
        "page_invalid": "La página debe ser un entero positivo.",
        "dose_below_one_bag": "La dosis es menor que la de un bulto para esta suerte.",
        "bags_mismatch": "Los bultos confirmados ({confirmed}) no coinciden con los calculados ({computed}). Revise de nuevo.",
        "session_invalid": "Sesión inválida o vencida.",
        "plot_not_found": "La suerte no existe.",
        "plot_forbidden": "La suerte no pertenece a la bodega de su sesión.",
        "duplicate_order": "Esa orden de fertilización ya fue despachada.",
        "limit_exceeded": "El despacho supera el límite de nitrógeno del ciclo. Disponible: {available} kg N/ha.",
        "too_large": "Solicitud demasiado grande.",
        "not_found": "Recurso no encontrado.",
        "method_not_allowed": "Método no permitido.",
        "internal_error": "Error interno.",
    },
    "en": {
        "order_format": "Use the format OF-YYYY-NNNN, for example OF-2026-1187.",
        "product_choice": "Choose one of: {options}.",
        "dose_number": "The dose must be a number.",
        "dose_range": "The dose must be greater than 0 and at most {max} kg/ha.",
        "dose_decimals": "The dose allows at most one decimal place.",
        "id_format": "The national id must have 6 to 10 digits.",
        "confirmed_bags_int": "Confirmed bags must be a positive integer.",
        "field_not_allowed": "Field not allowed.",
        "body_object": "The body must be a JSON object.",
        "content_type_json": "The content type must be application/json.",
        "invalid_json": "Invalid JSON.",
        "page_invalid": "The page must be a positive integer.",
        "dose_below_one_bag": "The dose is smaller than one bag for this plot.",
        "bags_mismatch": "Confirmed bags ({confirmed}) do not match the computed bags ({computed}). Review again.",
        "session_invalid": "Invalid or expired session.",
        "plot_not_found": "The plot does not exist.",
        "plot_forbidden": "The plot does not belong to your session's warehouse.",
        "duplicate_order": "That fertilization order has already been dispatched.",
        "limit_exceeded": "The dispatch exceeds the cycle nitrogen limit. Available: {available} kg N/ha.",
        "too_large": "Request too large.",
        "not_found": "Resource not found.",
        "method_not_allowed": "Method not allowed.",
        "internal_error": "Internal error.",
    },
}


def _language() -> str:
    """Pick the response language from the request's `Accept-Language` header.

    Returns:
        `"es"` or `"en"`; Spanish when the header is missing or unsupported.
    """
    return request.accept_languages.best_match(list(CATALOG), default=DEFAULT)


def number(value) -> str:
    """Decimal separator follows the language: comma in Spanish, point in English."""
    text = str(value)
    return text.replace(".", ",") if _language() == "es" else text


def translate(code: str, **params) -> str:
    """Translate a message code into the request's language.

    Args:
        code: Key in the message catalog (e.g. `"order_format"`).
        **params: Values interpolated into the message (e.g. `max=200`).

    Returns:
        The localised, formatted message.

    Raises:
        KeyError: If the code does not exist in the catalog.
    """
    return CATALOG[_language()][code].format(**params)
