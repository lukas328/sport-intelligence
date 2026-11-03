"""Annual subscription by Swiss QR bill (addendum 01, 4.10)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta

import pytest
from stdnum import iso11649

from handball_api.core.email import MemoryEmailSender
from handball_api.services import invoice_pdf
from handball_api.services.invoices import one_year_after, parse_camt054, rf_reference

from .conftest import Api, setup_club
from .test_ops import operators  # noqa: F401 (fixture)

pytestmark = pytest.mark.usefixtures("clean_db")

CONTACT = {
    "name": "HC Test",
    "attention": "Kassierin Petra Muster",
    "street": "Hallenweg 3",
    "pcode": "3011",
    "city": "Bern",
    "country": "CH",
    "email": "kasse@hc-test.ch",
    "locale": "de-CH",
}


def camt(ref: str, amount: str) -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.054.001.08"><BkToCstmrDbtCdtNtfctn><Ntfctn>
<Ntry><Amt Ccy="CHF">{amount}</Amt><CdtDbtInd>CRDT</CdtDbtInd><BookgDt><Dt>2026-11-20</Dt></BookgDt>
<NtryDtls><TxDtls><Amt Ccy="CHF">{amount}</Amt>
<RmtInf><Strd><CdtrRefInf><Ref>{ref}</Ref></CdtrRefInf></Strd></RmtInf></TxDtls></NtryDtls></Ntry>
<Ntry><Amt Ccy="CHF">10.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
<NtryDtls><TxDtls><Amt Ccy="CHF">10.00</Amt>
<RmtInf><Strd><CdtrRefInf><Ref>RF18539007547034</Ref></CdtrRefInf></Strd></RmtInf></TxDtls></NtryDtls></Ntry>
</Ntfctn></BkToCstmrDbtCdtNtfctn></Document>""".encode()


def test_helpers() -> None:
    ref = rf_reference("HB202600001")
    assert ref.startswith("RF") and iso11649.is_valid(ref)
    assert one_year_after(date(2026, 11, 3)) == date(2027, 11, 2)
    assert one_year_after(date(2028, 2, 29)) == date(2029, 2, 27)
    assert invoice_pdf.chf(390_00) == "390.00" and invoice_pdf.chf(1_990_50) == "1'990.50"
    entries = parse_camt054(camt(ref, "390.00"))
    assert entries[0] == {"reference": ref, "amount_cents": 39000, "booked": "2026-11-20"}


async def test_order_to_payment(
    make_api: Callable[[], Api],
    outbox: MemoryEmailSender,
    operators: None,  # noqa: F811
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    base = f"/v1/orgs/{org}/billing"
    price = (await api.get(f"{base}/annual", params={"plan": "team", "goalkeeper_seats": 1})).json()
    assert price["net_cents"] == (39 + 7) * 10 * 100 and price["months"] == 10
    assert price["contact"]["email"] == "coach@hc-test.ch"

    ops = make_api()
    await ops.register("ops@handball-ops.ch")
    r = await ops.post(
        "/v1/ops/vouchers", json={"code": "verband-be", "percent_off": 20, "note": "HV Bern"}
    )
    assert r.status_code == 201

    bad = await api.post(
        f"{base}/invoices", json={"plan": "team", "voucher": "NOPE", "contact": CONTACT}
    )
    assert bad.status_code == 422
    r = await api.post(
        f"{base}/invoices",
        json={"plan": "team", "goalkeeper_seats": 1, "voucher": "VERBAND-BE", "contact": CONTACT},
    )
    assert r.status_code == 201, r.text
    inv = r.json()
    assert (inv["net_cents"], inv["discount_cents"], inv["vat_cents"], inv["amount_cents"]) == (
        46000,
        9200,
        0,
        36800,
    )
    assert inv["number"].startswith(f"HB-{date.today().year}-") and iso11649.is_valid(
        inv["reference"]
    )
    mail = outbox.outbox[-1]
    assert mail.to == "kasse@hc-test.ch" and inv["number"] in mail.subject
    _, mime, pdf = mail.attachments[0]
    assert mime == "application/pdf" and pdf.startswith(b"%PDF") and len(pdf) > 10_000
    assert (await api.get(f"{base}/invoices/{inv['id']}/pdf")).content.startswith(b"%PDF")
    assert (
        await api.post(f"{base}/invoices", json={"plan": "team", "contact": CONTACT})
    ).status_code == 409

    # the plan works right away (payment term and dunning period)
    assert (await api.get(base)).json()["effective_plan"] == "team"

    # dunning: reminder after 3 days, final notice after 17
    from handball_api.core.db import enable_system_access, open_session
    from handball_api.services import invoices
    from handball_api.services.context import Ctx

    async def run(days: int) -> dict[str, int]:
        async with open_session() as db:
            ctx = Ctx(
                db=db,
                settings=api.app.state.settings,
                email=api.app.state.email,
                storage=api.app.state.storage,
            )
            await enable_system_access(db, reason="test")
            res = await invoices.run_dunning(ctx, date.today() + timedelta(days=days))
            await db.commit()
            return res

    assert await run(31) == {"reminders": 0, "dunning": 0, "lapsed": 0}  # 1 day overdue
    assert await run(33) == {"reminders": 1, "dunning": 0, "lapsed": 0}
    assert "Zahlungserinnerung" in outbox.outbox[-1].subject
    assert outbox.outbox[-1].attachments[0][2].startswith(b"%PDF")
    assert await run(47) == {"reminders": 0, "dunning": 1, "lapsed": 0}
    assert "Mahnung" in outbox.outbox[-1].subject
    assert await run(60) == {"reminders": 0, "dunning": 0, "lapsed": 1}
    assert await run(61) == {"reminders": 0, "dunning": 0, "lapsed": 0}

    # payment from the bank file: matched by reference and amount
    res = (
        await ops.post(
            "/v1/ops/invoices/camt054",
            files={"file": ("camt.xml", camt(inv["reference"], "368.00"), "application/xml")},
        )
    ).json()
    assert [m["number"] for m in res["matched"]] == [inv["number"]]
    assert res["unmatched"][0]["reason"] == "reference"
    paid = (await api.get(f"{base}/invoices")).json()[0]
    assert paid["paid_at"] is not None
    overview = (await api.get(base)).json()
    assert overview["effective_plan"] == "team" and overview["paid_until"]
    listed = (await ops.get("/v1/ops/invoices")).json()
    assert listed[0]["paid_at"] is not None
    assert (await api.get("/v1/ops/invoices")).status_code == 404
