"""Federations and volume licences (addendum 01 section 3, 5.10), invoices, club-to-club sharing."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from handball_api.core.db import Base, EntityMixin, TenantMixin
from handball_api.models._types import str_enum
from handball_api.models.enums import PaymentMethod


class Federation(Base, EntityMixin):
    """A federation or region buying licences for member clubs. Not tenant data: it spans clubs."""

    __tablename__ = "federations"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    contract_ref: Mapped[str | None] = mapped_column(String(120))
    contract_until: Mapped[date | None] = mapped_column(Date)
    seat_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class FederationAdmin(Base, EntityMixin):
    """Role `federation_admin`: manages the licence pool, sees no club content."""

    __tablename__ = "federation_admins"
    __table_args__ = (UniqueConstraint("federation_id", "user_id"),)

    federation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("federations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )


class FederationMembership(Base, EntityMixin, TenantMixin):
    """A club in a federation's licence pool (organization_id is the member club)."""

    __tablename__ = "federation_memberships"
    __table_args__ = (UniqueConstraint("federation_id", "organization_id"),)

    federation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("federations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    seats: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Invoice(Base, EntityMixin, TenantMixin):
    """Club invoice: card (Stripe) or QR bill with due date and dunning level (4.10)."""

    __tablename__ = "invoices"

    number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CHF")
    payment_method: Mapped[PaymentMethod] = mapped_column(str_enum(PaymentMethod), nullable=False)
    issued_on: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    dunning_level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stripe_invoice_id: Mapped[str | None] = mapped_column(String(80))
    pdf_key: Mapped[str | None] = mapped_column(String(300))


class OrgShare(Base, EntityMixin, TenantMixin):
    """P2 preparation: video exchange between clubs of a league, only with consent of both.

    organization_id owns the match; partner_org_id may see it once both accepted the terms.
    """

    __tablename__ = "org_shares"
    __table_args__ = (UniqueConstraint("match_id", "partner_org_id"),)

    partner_org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    terms_version: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    partner_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
