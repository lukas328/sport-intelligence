"""Plans, limits, Stripe checkout/portal and webhooks (M8)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from collections.abc import Callable, Iterator
from typing import Any

import asyncpg
import pytest
from fastapi import FastAPI

from handball_api.core.jobs import MemoryJobQueue

from .conftest import Api, setup_club
from .test_matches import new_match, upload

pytestmark = pytest.mark.usefixtures("clean_db")
SECRET = "whsec_test_secret"


class FakeGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def create_customer(self, name: str, email: str, org_id: str) -> str:
        self.calls.append(("customer", (name, email, org_id)))
        return "cus_123"

    async def checkout_url(
        self,
        customer: str,
        items: list[tuple[str, int]],
        trial_days: int,
        success_url: str,
        cancel_url: str,
        org_id: str,
    ) -> str:
        self.calls.append(("checkout", (customer, items, trial_days, success_url)))
        return "https://checkout.stripe.test/c/1"

    async def portal_url(self, customer: str, return_url: str) -> str:
        self.calls.append(("portal", (customer, return_url)))
        return "https://billing.stripe.test/p/1"

    async def remove_item(self, item_id: str) -> None:
        self.calls.append(("remove_item", (item_id,)))


@pytest.fixture
def billing_on(db_app: FastAPI) -> Iterator[FakeGateway]:
    s = db_app.state.settings
    old = (
        s.billing_enforce,
        s.stripe_price_team,
        s.stripe_price_club,
        s.stripe_price_goalkeeper,
        s.stripe_webhook_secret,
        db_app.state.billing,
    )
    from pydantic import SecretStr

    gw = FakeGateway()
    s.billing_enforce = True
    s.stripe_price_team, s.stripe_price_club, s.stripe_price_goalkeeper = (
        "price_team",
        "price_club",
        "price_gk",
    )
    s.stripe_webhook_secret = SecretStr(SECRET)
    db_app.state.billing = gw
    yield gw
    (
        s.billing_enforce,
        s.stripe_price_team,
        s.stripe_price_club,
        s.stripe_price_goalkeeper,
        s.stripe_webhook_secret,
        db_app.state.billing,
    ) = old


def signed(event: dict[str, Any]) -> tuple[bytes, dict[str, str]]:
    payload = json.dumps(event).encode()
    ts = int(time.time())
    sig = hmac.new(SECRET.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return payload, {"stripe-signature": f"t={ts},v1={sig}", "content-type": "application/json"}


def event(eid: str, etype: str, obj: dict[str, Any]) -> dict[str, Any]:
    return {"id": eid, "object": "event", "type": etype, "data": {"object": obj}}


async def test_overview_without_enforcement(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    b = (await api.get(f"/v1/orgs/{ids['org']}/billing")).json()
    assert (b["plan"], b["enforced"], b["checkout_available"]) == ("free", False, False)
    assert "tracking" in b["features"]
    assert [p["plan"] for p in b["plans"]] == ["free", "team", "club"]
    assert (
        await api.post(f"/v1/orgs/{ids['org']}/billing/checkout", json={"plan": "team"})
    ).status_code == 503


async def test_free_plan_limits(make_api: Callable[[], Api], billing_on: FakeGateway) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m1 = await new_match(api, ids)
    await new_match(api, ids)
    r = await api.post(
        f"/v1/orgs/{org}/teams/{ids['team']}/matches",
        json={"opponent_name": "Dritter", "kickoff_at": "2026-11-20T18:00:00+01:00"},
    )
    assert r.status_code == 402 and r.json()["type"].endswith("plan-limit-matches")
    r = await api.post(f"/v1/orgs/{org}/teams", json={"name": "Damen", "gender": "women"})
    assert r.status_code == 402 and r.json()["type"].endswith("plan-limit-teams")
    assert (await api.get(f"/v1/orgs/{org}/matches/{m1['id']}/insights")).status_code == 402
    assert (
        await api.get(f"/v1/orgs/{org}/teams/{ids['team']}/seasons/{ids['season']}/stats")
    ).status_code == 402
    # free: the video is processed but no tracking analysis starts
    await upload(api, ids, m1["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    token = {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}
    prefix = jobs.jobs[-1][3]["prefix"]
    await api.http.post(
        f"/internal/jobs/{jobs.jobs[-1][2]}",
        headers=token,
        json={"status": "succeeded", "progress": 1, "result": {"proxy_key": prefix + "proxy.mp4"}},
    )
    assert all(j[1] != "handball_gpu_worker.analysis.run_analysis" for j in jobs.jobs)
    b = (await api.get(f"/v1/orgs/{org}/billing")).json()
    assert b["usage"]["max_matches_per_season"] == 2
    assert b["usage"]["storage_bytes"] == 100
    assert b["features"] == ["events"]  # no goalkeeper module in the free plan (18.11.2026)
    assert (await api.get(f"/v1/orgs/{org}")).json()["features"] == ["events"]


async def test_gpu_minutes_from_analysis_runs(make_api: Callable[[], Api]) -> None:
    """The analysis worker reports `elapsed_s`; billing counts it as GPU time."""
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    await upload(api, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    token = {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}
    prefix = jobs.jobs[-1][3]["prefix"]
    await api.http.post(
        f"/internal/jobs/{jobs.jobs[-1][2]}",
        headers=token,
        json={"status": "succeeded", "progress": 1, "result": {"proxy_key": prefix + "proxy.mp4"}},
    )
    assert jobs.jobs[-1][1] == "handball_gpu_worker.analysis.run_analysis"
    analysis_id = jobs.jobs[-1][2]
    # progress callbacks carry no result and do not count
    await api.http.post(
        f"/internal/jobs/{analysis_id}", headers=token, json={"status": "running", "progress": 0.5}
    )
    await api.http.post(
        f"/internal/jobs/{analysis_id}",
        headers=token,
        json={
            "status": "succeeded",
            "progress": 1,
            "result": {"needs_calibration": True, "tracks": [], "elapsed_s": 90.0},
        },
    )
    b = (await api.get(f"/v1/orgs/{org}/billing")).json()
    assert b["usage"]["gpu_minutes"] == 1.5
    # a late duplicate callback does not count twice
    await api.http.post(
        f"/internal/jobs/{analysis_id}",
        headers=token,
        json={"status": "succeeded", "progress": 1, "result": {"elapsed_s": 600.0}},
    )
    assert (await api.get(f"/v1/orgs/{org}/billing")).json()["usage"]["gpu_minutes"] == 1.5


@pytest.mark.parametrize(
    ("result", "seconds"),
    [
        ({"elapsed_s": 12.5}, 12.5),
        ({"elapsed_s": 3}, 3.0),
        ({}, 0.0),
        ({"elapsed_s": "x"}, 0.0),
        ({"elapsed_s": True}, 0.0),
        ({"elapsed_s": -4}, 0.0),
    ],
)
def test_elapsed_seconds(result: dict[str, Any], seconds: float) -> None:
    from handball_api.services.videos import _elapsed_seconds

    assert _elapsed_seconds(result) == seconds


async def test_checkout_webhooks_and_portal(
    make_api: Callable[[], Api], billing_on: FakeGateway
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    assert (await api.post(f"/v1/orgs/{org}/billing/portal")).status_code == 409
    assert (
        await api.post(f"/v1/orgs/{org}/billing/checkout", json={"plan": "free"})
    ).status_code == 422
    r = await api.post(f"/v1/orgs/{org}/billing/checkout", json={"plan": "team"})
    assert r.json() == {"url": "https://checkout.stripe.test/c/1"}
    _kind, (customer, items, trial, success) = billing_on.calls[-1]
    # the goalkeeper functions are part of the plan: one item, no add-on (A9)
    assert (customer, items, trial) == ("cus_123", [("price_team", 1)], 30)
    assert success.endswith("?billing=success#billing")

    hook = "/v1/stripe/webhook"
    payload, headers = signed(
        event(
            "evt_1",
            "checkout.session.completed",
            {"client_reference_id": org, "customer": "cus_123", "subscription": "sub_1"},
        )
    )
    assert (await api.http.post(hook, content=payload, headers=headers)).json() == {
        "status": "processed"
    }
    assert (await api.http.post(hook, content=payload, headers=headers)).json() == {
        "status": "duplicate"
    }
    trial_end = int(time.time()) + 30 * 86400
    sub = {
        "id": "sub_1",
        "customer": "cus_123",
        "status": "trialing",
        "trial_end": trial_end,
        "items": {
            "data": [
                {"price": {"id": "price_team"}, "quantity": 1, "current_period_end": trial_end},
                {"id": "si_gk", "price": {"id": "price_gk"}, "quantity": 2},
            ]
        },
    }
    payload, headers = signed(event("evt_2", "customer.subscription.updated", sub))
    assert (await api.http.post(hook, content=payload, headers=headers)).status_code == 200
    b = (await api.get(f"/v1/orgs/{org}/billing")).json()
    assert (b["plan"], b["effective_plan"], b["status"]) == ("team", "team", "trialing")
    assert "goalkeeper_seats" not in b and "goalkeeper_addon_chf" not in b
    # a subscription booked with the former goalkeeper add-on runs on without it (A9)
    assert billing_on.calls[-1] == ("remove_item", ("si_gk",))
    # the goalkeeper module comes with Team, not with Gratis (18.11.2026)
    assert "tracking" in b["features"] and "goalkeepers" in b["features"]
    # paid features unlocked
    m = await new_match(api, ids)
    assert (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/insights")).status_code == 200
    # a second checkout no longer gets a trial
    await api.post(f"/v1/orgs/{org}/billing/checkout", json={"plan": "club"})
    # typed as the list's element: the remove_item assert above narrowed calls[-1]
    call: tuple[str, Any] = billing_on.calls[-1]
    kind, (_customer, _items, trial, _success) = call
    assert (kind, trial) == ("checkout", 0)
    assert (
        (await api.post(f"/v1/orgs/{org}/billing/portal"))
        .json()["url"]
        .startswith("https://billing")
    )

    payload, headers = signed(event("evt_3", "invoice.payment_failed", {"customer": "cus_123"}))
    await api.http.post(hook, content=payload, headers=headers)
    assert (await api.get(f"/v1/orgs/{org}/billing")).json()["status"] == "past_due"
    notes = (await api.get(f"/v1/orgs/{org}/me/notifications")).json()
    assert notes["items"][0]["kind"] == "payment_failed"

    payload, headers = signed(event("evt_4", "customer.subscription.deleted", sub))
    await api.http.post(hook, content=payload, headers=headers)
    b = (await api.get(f"/v1/orgs/{org}/billing")).json()
    assert (b["plan"], b["effective_plan"]) == ("free", "free")

    # signature and payload checks
    bad = dict(headers, **{"stripe-signature": "t=1,v1=deadbeef"})
    assert (await api.http.post(hook, content=payload, headers=bad)).status_code == 400
    payload, headers = signed(
        event("evt_5", "checkout.session.completed", {"client_reference_id": "nope"})
    )
    assert (await api.http.post(hook, content=payload, headers=headers)).json()[
        "status"
    ] == "processed"


async def test_stripe_gateway_requests() -> None:
    from types import SimpleNamespace

    from handball_api.services.billing import StripeGateway

    calls: list[dict[str, Any]] = []

    async def create(params: dict[str, Any]) -> Any:
        calls.append(params)
        return SimpleNamespace(id="cus_9", url="https://stripe.test/x")

    ns = SimpleNamespace(create_async=create)
    gw = StripeGateway("sk_test_123")
    gw.client = SimpleNamespace(  # type: ignore[assignment]
        v1=SimpleNamespace(
            customers=ns,
            checkout=SimpleNamespace(sessions=ns),
            billing_portal=SimpleNamespace(sessions=ns),
        )
    )
    assert await gw.create_customer("HC", "a@b.ch", "org-1") == "cus_9"
    url = await gw.checkout_url("cus_9", [("price_team", 1)], 30, "https://s", "https://c", "org-1")
    assert url == "https://stripe.test/x"
    assert calls[-1]["mode"] == "subscription"
    assert calls[-1]["subscription_data"]["trial_period_days"] == 30
    assert calls[-1]["client_reference_id"] == "org-1"
    await gw.checkout_url("cus_9", [("price_team", 1)], 0, "https://s", "https://c", "org-1")
    assert "trial_period_days" not in calls[-1]["subscription_data"]
    assert await gw.portal_url("cus_9", "https://r") == "https://stripe.test/x"


async def test_new_club_starts_the_trial_and_its_first_video_is_analysed(
    make_api: Callable[[], Api],
    billing_on: FakeGateway,
    db_app: FastAPI,
    owner_conn: asyncpg.Connection,
) -> None:
    # UX test, second delivery: a club made at sign-up gets the Team plan's trial without payment
    # details, so its first video is analysed; after the trial it falls back to Free
    db_app.state.settings.trial_on_signup = True
    api = make_api()
    ids = await setup_club(api)
    b = (await api.get(f"/v1/orgs/{ids['org']}/billing")).json()
    assert (b["plan"], b["effective_plan"]) == ("team", "team")
    assert b["trial_ends_at"] is not None
    assert "tracking" in b["features"]
    # the trial is used (a later checkout starts no second one); when it ends, Free again
    assert await owner_conn.fetchval(
        "SELECT trial_used FROM organizations WHERE id = $1", uuid.UUID(ids["org"])
    )
    await owner_conn.execute(
        "UPDATE organizations SET trial_ends_at = now() - interval '1 day' WHERE id = $1",
        uuid.UUID(ids["org"]),
    )
    b = (await api.get(f"/v1/orgs/{ids['org']}/billing")).json()
    assert (b["plan"], b["effective_plan"]) == ("team", "free")


def test_currency_from_the_country() -> None:
    """Europa step 2 (EU3): clubs in Switzerland and Liechtenstein pay in CHF, all others in EUR,
    the same number."""
    from handball_api.models.enums import Plan
    from handball_api.services.plans import PLANS, currency_for

    assert [currency_for(c) for c in ("CH", "LI", "li", None)] == ["CHF"] * 4
    assert [currency_for(c) for c in ("DE", "FR", "AT", "SE")] == ["EUR"] * 4
    assert PLANS[Plan.TEAM].price_month == 39 and PLANS[Plan.CLUB].price_month == 199


async def test_club_abroad_pays_in_eur(
    make_api: Callable[[], Api], billing_on: FakeGateway, owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    await owner_conn.execute(
        "UPDATE organizations SET country = 'DE' WHERE id = $1", uuid.UUID(org)
    )
    overview = (await api.get(f"/v1/orgs/{org}/billing")).json()
    assert overview["currency"] == "EUR"
    assert {p["plan"]: p["price_month"] for p in overview["plans"]} == {
        "free": 0,
        "team": 39,
        "club": 199,
    }
    # no EUR price configured: no card checkout in EUR (never the CHF price instead)
    r = await api.post(f"/v1/orgs/{org}/billing/checkout", json={"plan": "team"})
    assert r.status_code == 503
    s = api.app.state.settings
    s.stripe_price_team_eur = "price_team_eur"
    try:
        r = await api.post(f"/v1/orgs/{org}/billing/checkout", json={"plan": "team"})
        assert r.status_code == 200, r.text
        _kind, (_customer, items, _trial, _success) = billing_on.calls[-1]
        assert items == [("price_team_eur", 1)]
        from handball_api.models.enums import Plan
        from handball_api.services.billing import _plan_for

        # a subscription with the EUR price is the same plan
        assert _plan_for(s, ["price_team_eur"]) == Plan.TEAM
        assert _plan_for(s, ["price_team"]) == Plan.TEAM
    finally:
        s.stripe_price_team_eur = None
