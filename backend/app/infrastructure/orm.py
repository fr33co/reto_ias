"""SQLAlchemy declarative models. Constraints live in the database, not only in the app."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer,
                        Numeric, String, Text, Uuid)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base of the ORM models."""
    pass


class PlotORM(Base):
    """Table `plots`: crop plots and the start of their current cycle."""
    __tablename__ = "plots"
    code: Mapped[str] = mapped_column(String(5), primary_key=True)
    warehouse: Mapped[str] = mapped_column(String(5))
    gross_area_ha: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    net_area_ha: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    cycle_start: Mapped[date] = mapped_column(Date)
    cycle_origin: Mapped[str] = mapped_column(String(7))
    irrigation: Mapped[str] = mapped_column(String(11))
    __table_args__ = (
        CheckConstraint("code ~ '^S-[0-9]{3}$'", name="ck_plot_code"),
        CheckConstraint("warehouse IN ('NORTE', 'SUR')", name="ck_plot_warehouse"),
        CheckConstraint("net_area_ha > 0 AND net_area_ha <= gross_area_ha", name="ck_plot_area"),
        CheckConstraint("cycle_origin IN ('CORTE', 'SIEMBRA')", name="ck_plot_origin"),
        CheckConstraint("irrigation IN ('SURCOS', 'FERTIRRIEGO')", name="ck_plot_irrigation"),
    )


class DispatchORM(Base):
    """Table `dispatches`: append-only; the database rejects UPDATE and DELETE (trigger)."""
    __tablename__ = "dispatches"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(12), unique=True)
    plot: Mapped[str] = mapped_column(ForeignKey("plots.code"))
    product: Mapped[str] = mapped_column(String(3))
    dose_kg_ha: Mapped[Decimal] = mapped_column(Numeric(4, 1))
    bags: Mapped[int] = mapped_column(Integer)
    delivered_kg: Mapped[int] = mapped_column(Integer)
    n_grams: Mapped[int] = mapped_column(BigInteger)
    foreman_encrypted_id: Mapped[str] = mapped_column(Text)     # full national id, Fernet-encrypted
    foreman_last4: Mapped[str] = mapped_column(String(4))
    counter: Mapped[str] = mapped_column(String(10))
    registered_by: Mapped[str] = mapped_column(String(20))
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    local_date: Mapped[date] = mapped_column(Date)               # America/Bogota day; defines the cycle
    __table_args__ = (
        CheckConstraint("order_no ~ '^OF-[0-9]{4}-[0-9]{4}$'", name="ck_dispatch_order"),
        CheckConstraint("product IN ('URE', 'SAM', 'DAP', 'KCL')", name="ck_dispatch_product"),
        CheckConstraint("dose_kg_ha > 0 AND dose_kg_ha <= 200", name="ck_dispatch_dose"),
        CheckConstraint("bags > 0 AND delivered_kg > 0 AND n_grams >= 0", name="ck_dispatch_amounts"),
        # Cycle sum served by the index (INCLUDE avoids touching the table) + history page.
        Index("dispatches_plot_date", "plot", local_date.desc(), registered_at.desc(), "id",
              postgresql_include=["n_grams"]),
    )
