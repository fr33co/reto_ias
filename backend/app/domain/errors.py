"""Domain exceptions. The API layer maps each one to an HTTP status."""
from dataclasses import dataclass, field


class DomainError(Exception):
    """Base class of all domain errors."""
    pass


class PlotNotFound(DomainError):
    """The plot does not exist."""
    pass


class AccessDenied(DomainError):
    """The plot belongs to another warehouse than the session's."""
    pass


class DuplicateOrder(DomainError):
    """The fertilization order was already dispatched."""
    pass


@dataclass(frozen=True)
class FieldError:
    """A validation problem: the API field, a translation key and its parameters."""
    field: str
    code: str
    params: dict = field(default_factory=dict)


class InvalidData(DomainError):
    """One or more fields are invalid."""

    def __init__(self, errors: list[FieldError]):
        """Initialise the instance.

        Args:
            errors: One `FieldError` per wrong field.
        """
        super().__init__("invalid data")
        self.errors = errors


class NitrogenLimitExceeded(DomainError):
    """The dispatch would exceed the cycle's nitrogen limit."""

    def __init__(self, dispatch_n_g: int, max_bags: int | None, balance):
        """Initialise the instance.

        Args:
            dispatch_n_g: Nitrogen (grams) the rejected dispatch would add.
            max_bags: Bags of that product that still fit (`None` if the product has no N).
            balance: The plot's current balance.
        """
        super().__init__("nitrogen limit exceeded")
        self.dispatch_n_g = dispatch_n_g
        self.max_bags = max_bags
        self.balance = balance
