"""Sensors (position, heart rate, load): CSV import, Kinexon and Polar stubs.

Health data is minimised: only what the physical load view needs (P6/P7)."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Protocol

from handball_api.integrations.base import AdapterError, Stub


@dataclass(frozen=True)
class Sample:
    t_ms: int
    number: int
    x: float | None = None
    y: float | None = None
    heart_rate: int | None = None
    load: float | None = None


class WearableAdapter(Protocol):
    name: str

    def samples(self, payload: str) -> list[Sample]: ...


def _num(v: str | None) -> float | None:
    v = (v or "").strip().replace(",", ".")
    return float(v) if v else None


class CsvWearable:
    """Columns: t_ms, number, x, y (metres, 0..40 / 0..20), heart_rate, load. Only t_ms and
    number are required."""

    name = "csv"

    def samples(self, payload: str) -> list[Sample]:
        reader = csv.DictReader(io.StringIO(payload), delimiter=";" if ";" in payload else ",")
        out: list[Sample] = []
        for i, r in enumerate(reader, start=2):
            try:
                x, y = _num(r.get("x")), _num(r.get("y"))
                if (x is not None and not 0 <= x <= 40) or (y is not None and not 0 <= y <= 20):
                    raise AdapterError(f"Row {i}: position outside the court")
                hr = _num(r.get("heart_rate"))
                out.append(
                    Sample(
                        t_ms=int(r["t_ms"]),
                        number=int(r["number"]),
                        x=x,
                        y=y,
                        heart_rate=int(hr) if hr is not None else None,
                        load=_num(r.get("load")),
                    )
                )
            except (KeyError, ValueError, TypeError) as exc:
                raise AdapterError(f"Row {i}: t_ms and number are required numbers") from exc
        return sorted(out, key=lambda s: (s.t_ms, s.number))


class KinexonWearable(Stub):
    name = partner = "kinexon"

    def samples(self, payload: str) -> list[Sample]:
        raise self._missing()


class PolarWearable(Stub):
    name = partner = "polar"

    def samples(self, payload: str) -> list[Sample]:
        raise self._missing()
