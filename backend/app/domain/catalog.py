"""Product catalog and business constants (configuration, not persistence)."""
from dataclasses import dataclass

LIMIT_N_KG_HA = 160       # kg of N per net hectare per crop cycle
PAGE_SIZE = 50            # history rows per page
MAX_DOSE_KG_HA = 200


@dataclass(frozen=True)
class Product:
    """A fertilizer product from the catalog.

    Attributes:
        code: Product code (`URE`, `SAM`, `DAP`, `KCL`).
        name: Descriptive name.
        bag_kg: Kilograms per closed bag.
        n_pct, p2o5_pct, k2o_pct: Percentage of each nutrient.
        main_nutrient: The nutrient the dose is expressed in (`N`, `P2O5` or `K2O`).
    """
    code: str
    name: str
    bag_kg: int
    n_pct: int
    p2o5_pct: int
    k2o_pct: int
    main_nutrient: str  # "N" | "P2O5" | "K2O"

    @property
    def main_pct(self) -> int:
        """Percentage of the main nutrient (the one the dose is expressed in)."""
        return {"N": self.n_pct, "P2O5": self.p2o5_pct, "K2O": self.k2o_pct}[self.main_nutrient]


PRODUCTS: dict[str, Product] = {
    p.code: p
    for p in (
        Product("URE", "Urea", 50, 46, 0, 0, "N"),
        Product("SAM", "Ammonium sulfate", 50, 21, 0, 0, "N"),
        Product("DAP", "Diammonium phosphate", 50, 18, 46, 0, "P2O5"),
        Product("KCL", "Potassium chloride", 50, 0, 0, 60, "K2O"),
    )
}
