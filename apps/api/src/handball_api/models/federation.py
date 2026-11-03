"""Federations and volume licences (addendum 01 section 3, 5.10), invoices, club-to-club sharing."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
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
    plan: Mapped[str] = mapped_column(String(10), nullable=False, default="team")
    # recipient of the joint invoice (name, street, pcode, city, country, attention, email)
    billing_address: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class FederationInvite(Base, EntityMixin):
    """A federation invites a club by e-mail; a club admin accepts with the link (5.10)."""

    __tablename__ = "federation_invites"

    federation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("federations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL")
    )


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
    plan: Mapped[str | None] = mapped_column(String(20))
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    net_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vat_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vat_rate_bp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 810 = 8.10 %
    reference: Mapped[str | None] = mapped_column(String(40), unique=True)  # RF creditor ref.
    voucher_code: Mapped[str | None] = mapped_column(String(40))
    lines: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    recipient: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_note: Mapped[str | None] = mapped_column(String(200))


class Voucher(Base, EntityMixin):
    """Discount code (federation contracts, volume discounts); managed in the backoffice."""

    __tablename__ = "vouchers"

    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    percent_off: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    federation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("federations.id", ondelete="SET NULL")
    )
    valid_until: Mapped[date | None] = mapped_column(Date)
    max_uses: Mapped[int | None] = mapped_column(Integer)
    uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(String(200))


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
