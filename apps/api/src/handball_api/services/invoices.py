"""Annual subscription by invoice with Swiss QR bill (addendum 01, 4.10).

Order -> invoice (PDF with QR payment part, e-mail to the treasurer) -> reminder after 3 days
overdue -> final notice after 17 days -> plan falls back after 30 days overdue. Payment is marked in
the backoffice or matched from a camt.054 bank file (QR reference and amount).
"""

from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, update
from stdnum import iso11649

from handball_api.core.db import disable_system_access, enable_system_access, set_tenant
from handball_api.core.email import Email, try_send
from handball_api.core.errors import ProblemError
from handball_api.models import Invoice, Organization, OrgMembership, User, Voucher
from handball_api.models.enums import OrgRole, PaymentMethod, Plan
from handball_api.services import audit, invoice_pdf
from handball_api.services.context import Ctx
from handball_api.services.plans import GOALKEEPER_ADDON_CHF, PLANS
from handball_api.services.policies import Action, authorize

REMINDER_DAYS = 3
DUNNING_DAYS = 17
CUTOFF_DAYS = 30
INVOICE_STATES = ("invoice_open", "invoice_paid")

MAIL = {
    "de-CH": {
        "invoice": (
            "Rechnung {number} von {creditor}",
            "Guten Tag\n\nim Anhang die Rechnung {number} für das Jahresabo {plan} ({total}). Zahlbar bis {due}.\n\nFreundliche Grüsse\n{creditor}",
        ),
        "reminder": (
            "Zahlungserinnerung zu Rechnung {number}",
            "Guten Tag\n\ndie Rechnung {number} über {total} war am {due} fällig. Vielleicht ist sie untergegangen: im Anhang nochmals mit Einzahlungsschein. Falls schon bezahlt, betrachte diese Nachricht als gegenstandslos.\n\nFreundliche Grüsse\n{creditor}",
        ),
        "dunning": (
            "Mahnung zu Rechnung {number}",
            "Guten Tag\n\ndie Rechnung {number} über {total} ist weiterhin offen. Bitte bezahle sie in den nächsten 14 Tagen, sonst wird das Abo auf die Gratisversion zurückgestuft. Videos und Daten bleiben erhalten.\n\nFreundliche Grüsse\n{creditor}",
        ),
    },
    "fr": {
        "invoice": (
            "Facture {number} de {creditor}",
            "Bonjour\n\nVous trouverez ci-joint la facture {number} pour l'abonnement annuel {plan} ({total}). Payable jusqu'au {due}.\n\nMeilleures salutations\n{creditor}",
        ),
        "reminder": (
            "Rappel de paiement pour la facture {number}",
            "Bonjour\n\nLa facture {number} de {total} était due le {due}. Elle est jointe à nouveau avec le bulletin de versement. Si elle est déjà payée, merci de ne pas tenir compte de ce message.\n\nMeilleures salutations\n{creditor}",
        ),
        "dunning": (
            "Sommation pour la facture {number}",
            "Bonjour\n\nLa facture {number} de {total} est toujours ouverte. Merci de la payer dans les 14 jours, sinon l'abonnement passera à la version gratuite. Les vidéos et données sont conservées.\n\nMeilleures salutations\n{creditor}",
        ),
    },
    "en": {
        "invoice": (
            "Invoice {number} from {creditor}",
            "Hello\n\nAttached is invoice {number} for the annual {plan} subscription ({total}). Due on {due}.\n\nKind regards\n{creditor}",
        ),
        "reminder": (
            "Payment reminder for invoice {number}",
            "Hello\n\nInvoice {number} for {total} was due on {due}. It is attached again with the payment slip. If you have already paid, please ignore this message.\n\nKind regards\n{creditor}",
        ),
        "dunning": (
            "Final notice for invoice {number}",
            "Hello\n\nInvoice {number} for {total} is still open. Please pay within 14 days, otherwise the subscription falls back to the free version. Videos and data are kept.\n\nKind regards\n{creditor}",
        ),
    },
}


def _today() -> date:
    return datetime.now(UTC).date()


def rf_reference(body: str) -> str:
    """ISO 11649 creditor reference (RF...) for a QR bill with a normal IBAN."""
    body = "".join(ch for ch in body.upper() if ch.isalnum())[:21]
    digits = "".join(str(int(ch, 36)) for ch in body + "RF00")
    ref = f"RF{98 - int(digits) % 97:02d}{body}"
    iso11649.validate(ref)
    return ref


def one_year_after(start: date) -> date:
    """Last day of a one-year period (a period starting on 29 February ends on 27 February)."""
    try:
        return date(start.year + 1, start.month, start.day) - timedelta(days=1)
    except ValueError:
        return date(start.year + 1, 2, 27)


def price_cents(ctx: Ctx, plan: Plan, goalkeepers: int) -> int:
    months = ctx.settings.invoice_annual_months
    return (PLANS[plan].price_chf_month + goalkeepers * GOALKEEPER_ADDON_CHF) * months * 100


def creditor(ctx: Ctx) -> dict[str, str]:
    s = ctx.settings
    return {
        "name": s.invoice_creditor_name,
        "street": s.invoice_creditor_street,
        "pcode": s.invoice_creditor_pcode,
        "city": s.invoice_creditor_city,
        "country": s.invoice_creditor_country,
    }


def _inv_dict(inv: Invoice) -> dict[str, Any]:
    return {
        "number": inv.number,
        "recipient": inv.recipient,
        "issued_on": inv.issued_on,
        "due_date": inv.due_date,
        "period_start": inv.period_start,
        "period_end": inv.period_end,
        "lines": inv.lines,
        "net_cents": inv.net_cents,
        "discount_cents": inv.discount_cents,
        "vat_cents": inv.vat_cents,
        "vat_rate_bp": inv.vat_rate_bp,
        "total_cents": inv.amount_cents,
        "reference": inv.reference,
        "voucher_code": inv.voucher_code,
    }


def render_pdf(ctx: Ctx, inv: Invoice, kind: str = "invoice") -> bytes:
    s = ctx.settings
    return invoice_pdf.render(
        str(inv.recipient.get("locale") or "de-CH"),
        creditor(ctx),
        s.invoice_iban,
        s.invoice_uid if s.invoice_vat_registered else None,
        _inv_dict(inv),
        s.invoice_payment_days,
        kind,
    )


async def _send(ctx: Ctx, inv: Invoice, kind: str) -> bool:
    """False when the provider failed (logged); the invoice itself stays valid."""
    lang = str(inv.recipient.get("locale") or "de-CH")
    subject, body = MAIL.get(lang, MAIL["de-CH"])[kind]
    params = {
        "number": inv.number,
        "creditor": ctx.settings.invoice_creditor_name,
        "plan": (inv.plan or "").title(),
        "total": f"CHF {invoice_pdf.chf(inv.amount_cents)}",
        "due": inv.due_date.strftime("%d.%m.%Y"),
    }
    return await try_send(
        ctx.email,
        Email(
            to=str(inv.recipient["email"]),
            subject=subject.format(**params),
            text=body.format(**params),
            attachments=((f"{inv.number}.pdf", "application/pdf", render_pdf(ctx, inv, kind)),),
        ),
        f"invoice_{kind}",
        invoice_id=str(inv.id),
    )


async def _voucher(ctx: Ctx, code: str | None) -> Voucher | None:
    if not code:
        return None
    v = await ctx.db.scalar(select(Voucher).where(func.upper(Voucher.code) == code.strip().upper()))
    today = _today()
    if (
        v is None
        or (v.valid_until and v.valid_until < today)
        or (v.max_uses is not None and v.uses >= v.max_uses)
    ):
        raise ProblemError(422, "invalid-voucher", "The voucher is not valid")
    return v


async def _next_number(ctx: Ctx, year: int) -> str:
    await enable_system_access(ctx.db, reason="invoice numbering")
    try:
        n = await ctx.db.scalar(
            select(func.count(Invoice.id)).where(Invoice.number.like(f"HB-{year}-%"))
        )
    finally:
        await disable_system_access(ctx.db)
    return f"HB-{year}-{(n or 0) + 1:05d}"


async def order(
    ctx: Ctx, plan: Plan, goalkeepers: int, voucher_code: str | None, contact: dict[str, str]
) -> Invoice:
    actor = ctx.require_actor()
    authorize(actor, Action.ORG_UPDATE, two_factor=ctx.two_factor)
    if plan == Plan.FREE:
        raise ProblemError(422, "validation", "Choose a paid plan")
    org = await ctx.db.get(Organization, actor.organization_id)
    assert org is not None
    open_inv = await ctx.db.scalar(
        select(Invoice.id).where(
            Invoice.organization_id == org.id,
            Invoice.paid_at.is_(None),
            Invoice.cancelled_at.is_(None),
        )
    )
    if open_inv:
        raise ProblemError(409, "invoice-open", "There is an open invoice already")
    voucher = await _voucher(ctx, voucher_code)
    s = ctx.settings
    net = price_cents(ctx, plan, goalkeepers)
    discount = net * (voucher.percent_off if voucher else 0) // 100
    vat_bp = round(s.invoice_vat_rate_percent * 100) if s.invoice_vat_registered else 0
    vat = round((net - discount) * vat_bp / 10_000)
    today = _today()
    start = max(today, org.paid_until.date() if org.paid_until else today)
    end = one_year_after(start)
    number = await _next_number(ctx, today.year)
    lines = [
        {
            "text": f"Jahresabo {plan.value.title()} ({s.invoice_annual_months} Monatspreise)",
            "cents": PLANS[plan].price_chf_month * s.invoice_annual_months * 100,
        }
    ]
    if goalkeepers:
        lines.append(
            {
                "text": f"Torhüter-Modul x {goalkeepers}",
                "cents": goalkeepers * GOALKEEPER_ADDON_CHF * s.invoice_annual_months * 100,
            }
        )
    org.billing_contact = contact
    inv = Invoice(
        organization_id=org.id,
        number=number,
        amount_cents=net - discount + vat,
        net_cents=net,
        discount_cents=discount,
        vat_cents=vat,
        vat_rate_bp=vat_bp,
        payment_method=PaymentMethod.INVOICE_QR,
        issued_on=today,
        due_date=today + timedelta(days=s.invoice_payment_days),
        plan=plan.value,
        period_start=start,
        period_end=end,
        reference=rf_reference(number.replace("-", "")),
        voucher_code=voucher.code if voucher else None,
        lines=lines,
        recipient={**contact, "name": contact.get("name") or org.name},
    )
    ctx.db.add(inv)
    if voucher:
        # vouchers are platform data: counting a use needs system access (RLS)
        await enable_system_access(ctx.db, reason="voucher use")
        try:
            await ctx.db.execute(
                update(Voucher).where(Voucher.id == voucher.id).values(uses=Voucher.uses + 1)
            )
        finally:
            await disable_system_access(ctx.db)
        await ctx.db.refresh(voucher)
    org.plan = plan
    org.subscription_status = "invoice_open"
    # usable during the payment term and the dunning period
    org.paid_until = datetime.combine(
        inv.due_date + timedelta(days=CUTOFF_DAYS), datetime.min.time(), UTC
    )
    await ctx.db.flush()
    pdf = render_pdf(ctx, inv)
    key = f"{org.id}/invoices/{inv.number}.pdf"
    await ctx.storage.put(ctx.settings.s3_bucket_artifacts, key, pdf, "application/pdf")
    inv.pdf_key = key
    await _send(ctx, inv, "invoice")
    await audit.record(
        ctx, "invoice.created", target_type="invoice", target_id=inv.id, data={"number": number}
    )
    return inv


async def list_for_org(ctx: Ctx) -> list[Invoice]:
    actor = ctx.require_actor()
    authorize(actor, Action.ORG_UPDATE, two_factor=ctx.two_factor)
    rows = await ctx.db.scalars(
        select(Invoice)
        .where(Invoice.organization_id == actor.organization_id)
        .order_by(Invoice.issued_on.desc())
    )
    return list(rows.all())


async def pdf(ctx: Ctx, invoice_id: uuid.UUID) -> tuple[bytes, str]:
    actor = ctx.require_actor()
    authorize(actor, Action.ORG_UPDATE, two_factor=ctx.two_factor)
    inv = await ctx.db.get(Invoice, invoice_id)
    if inv is None or inv.organization_id != actor.organization_id or not inv.pdf_key:
        raise ProblemError(404, "not-found", "Invoice not found")
    data, _ = await ctx.storage.get(ctx.settings.s3_bucket_artifacts, inv.pdf_key)
    return data, f"{inv.number}.pdf"


# ---- operator side (system access) ---------------------------------------------------------


async def mark_paid(
    ctx: Ctx, invoice_id: uuid.UUID, note: str | None, when: datetime | None = None
) -> Invoice:
    inv = await ctx.db.get(Invoice, invoice_id)
    if inv is None:
        raise ProblemError(404, "not-found", "Invoice not found")
    if inv.paid_at is None:
        inv.paid_at = when or datetime.now(UTC)
        inv.paid_note = (note or "")[:200] or None
        org = await ctx.db.get(Organization, inv.organization_id)
        if org is not None and inv.period_end:
            org.subscription_status = "invoice_paid"
            org.paid_until = datetime.combine(
                inv.period_end + timedelta(days=1), datetime.min.time(), UTC
            )
            org.trial_used = True
        await audit.record(
            ctx,
            "invoice.paid",
            org_id=inv.organization_id,
            target_type="invoice",
            target_id=inv.id,
            data={"note": note},
        )
    return inv


async def open_invoices(ctx: Ctx) -> list[dict[str, Any]]:
    rows = (
        await ctx.db.execute(
            select(Invoice, Organization.name)
            .join(Organization, Organization.id == Invoice.organization_id)
            .where(Invoice.cancelled_at.is_(None))
            .order_by(Invoice.issued_on.desc())
            .limit(500)
        )
    ).all()
    return [
        {
            "id": str(i.id),
            "number": i.number,
            "organization": name,
            "amount_cents": i.amount_cents,
            "due_date": i.due_date.isoformat(),
            "dunning_level": i.dunning_level,
            "paid_at": i.paid_at.isoformat() if i.paid_at else None,
            "reference": i.reference,
        }
        for i, name in rows
    ]


NS = {"c": "urn:iso:std:iso:20022:tech:xsd:camt.054.001.08"}


def parse_camt054(xml: bytes) -> list[dict[str, Any]]:
    """Credit entries of a camt.054 file: reference, amount (cents), booking date."""
    root = ET.fromstring(xml)  # noqa: S314 (operator-uploaded bank file, no external entities in ET)
    ns = root.tag.split("}")[0].strip("{") if root.tag.startswith("{") else ""
    q = (lambda tag: f"{{{ns}}}{tag}") if ns else (lambda tag: tag)
    out = []
    for ntry in root.iter(q("Ntry")):
        cd = ntry.findtext(q("CdtDbtInd"))
        booked = ntry.findtext(f"{q('BookgDt')}/{q('Dt')}")
        for tx in ntry.iter(q("TxDtls")):
            ref = tx.findtext(f"{q('RmtInf')}/{q('Strd')}/{q('CdtrRefInf')}/{q('Ref')}")
            amt = tx.findtext(f"{q('Amt')}") or tx.findtext(
                f"{q('AmtDtls')}/{q('TxAmt')}/{q('Amt')}"
            )
            if cd == "CRDT" and ref and amt:
                out.append(
                    {
                        "reference": ref.replace(" ", ""),
                        "amount_cents": int(Decimal(amt) * 100),
                        "booked": booked,
                    }
                )
    return out


async def match_camt054(ctx: Ctx, xml: bytes) -> dict[str, list[dict[str, Any]]]:
    matched, unmatched = [], []
    for entry in parse_camt054(xml):
        inv = await ctx.db.scalar(select(Invoice).where(Invoice.reference == entry["reference"]))
        if inv is not None and inv.amount_cents == entry["amount_cents"]:
            await mark_paid(ctx, inv.id, f"camt.054 {entry.get('booked') or ''}".strip())
            matched.append({**entry, "number": inv.number})
        else:
            unmatched.append({**entry, "reason": "amount" if inv is not None else "reference"})
    return {"matched": matched, "unmatched": unmatched}


async def run_dunning(ctx: Ctx, today: date | None = None) -> dict[str, int]:
    """Daily: reminder after 3 days overdue, final notice after 17, plan falls back after 30."""
    today = today or _today()
    counts = {"reminders": 0, "dunning": 0, "lapsed": 0}
    rows = list(
        (
            await ctx.db.scalars(
                select(Invoice).where(
                    Invoice.paid_at.is_(None),
                    Invoice.cancelled_at.is_(None),
                    Invoice.payment_method == PaymentMethod.INVOICE_QR,
                )
            )
        ).all()
    )
    for inv in rows:
        overdue = (today - inv.due_date).days
        await set_tenant(ctx.db, inv.organization_id)
        await enable_system_access(ctx.db, reason="dunning run")
        # a level only counts once its mail went out, so a failed mail is retried next run
        if overdue >= DUNNING_DAYS and inv.dunning_level < 2:
            if await _send(ctx, inv, "dunning"):
                inv.dunning_level = 2
                inv.reminded_at = datetime.now(UTC)
                counts["dunning"] += 1
        elif (
            overdue >= REMINDER_DAYS and inv.dunning_level < 1 and await _send(ctx, inv, "reminder")
        ):
            inv.dunning_level = 1
            inv.reminded_at = datetime.now(UTC)
            counts["reminders"] += 1
        if overdue >= CUTOFF_DAYS and inv.dunning_level < 3:
            inv.dunning_level = 3
            counts["lapsed"] += 1
    await ctx.db.flush()
    return counts


async def treasurer_default(ctx: Ctx, org: Organization) -> dict[str, str]:
    """Prefill for the order form: the stored contact or the first club admin."""
    if org.billing_contact:
        return dict(org.billing_contact)
    email = await ctx.db.scalar(
        select(User.email)
        .join(OrgMembership, OrgMembership.user_id == User.id)
        .where(OrgMembership.role == OrgRole.ORG_ADMIN)
        .limit(1)
    )
    return {"name": org.name, "email": email or "", "country": "CH"}


async def list_vouchers(ctx: Ctx) -> list[dict[str, Any]]:
    rows = await ctx.db.scalars(select(Voucher).order_by(Voucher.created_at.desc()))
    return [
        {
            "code": v.code,
            "percent_off": v.percent_off,
            "valid_until": v.valid_until.isoformat() if v.valid_until else None,
            "max_uses": v.max_uses,
            "uses": v.uses,
            "note": v.note,
        }
        for v in rows.all()
    ]


async def create_voucher(ctx: Ctx, data: dict[str, Any]) -> dict[str, Any]:
    code = str(data["code"]).upper()
    if await ctx.db.scalar(select(Voucher.id).where(func.upper(Voucher.code) == code)):
        raise ProblemError(409, "duplicate-name", "This code exists")
    ctx.db.add(Voucher(**{**data, "code": code}))
    await ctx.db.flush()
    await audit.record(ctx, "voucher.created", org_id=None, data={"code": code})
    return {"code": code, "percent_off": data["percent_off"]}
