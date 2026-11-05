"""Name parsing and fuzzy team matching of ml/data/match_official.py (no network)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from match_official import Match, find_match, league_filter, parse_name, score_game, team_score


def test_parse_exact_date() -> None:
    p = parse_name("CH_NLB_SGWaedenswilHorgen_YellowPfadiEspoirs_2022-09-11")
    assert p.country == "CH"
    assert p.league == ["NLB"]
    assert p.teams == ["SGWaedenswilHorgen", "YellowPfadiEspoirs"]
    assert p.day == date(2022, 9, 11)
    assert p.date_kind == "exact"


def test_parse_approx_and_parts() -> None:
    p = parse_name("CH_Frauen_SPL2_HCArbon_HSGLeimental_hz1_ca2025")
    assert p.women
    assert p.teams == ["HCArbon", "HSGLeimental"]
    assert p.tags == ["hz1"]
    assert p.date_kind == "approx"
    assert p.date_from == date(2024, 1, 1)
    assert p.date_to == date(2026, 12, 31)


def test_parse_month_year_and_single_team() -> None:
    assert parse_name("CH_RegioCup_Final_Herren_2017-03").teams == []
    assert parse_name("CH_RegioCup_Final_Herren_2017-03").date_to == date(2017, 3, 31)
    p = parse_name("CH_Frauen_1Liga_vs_STVWillisau_2019-02-23")
    assert p.teams == ["STVWillisau"]
    assert parse_name("CH_NLA_Finalissima_WackerThun_Kadetten_2013").date_kind == "year"


def test_team_score_umlauts_prefixes_and_variants() -> None:
    assert team_score("SGWaedenswilHorgen", "SG Wädenswil/Horgen") == 1.0
    assert team_score("YellowPfadiEspoirs", "SG Yellow/ Pfadi Espoirs") == 1.0
    assert team_score("Chenois", "CS Chênois Genève Handball") == 1.0
    assert team_score("SpOno2", "SPONO Eagles 2") == 1.0
    assert team_score("Niederlande", "Holland") == 1.0
    # second teams and youth teams the name does not mention rank lower
    assert team_score("SGWaedenswilHorgen", "SG Wädenswil/Horgen 2 *") < 0.7
    assert team_score("Kadetten", "SG GS/Kadetten Espoirs SH") < team_score(
        "Kadetten", "Kadetten Schaffhausen (QHL)")
    assert team_score("LKZug2", "LK Zug Handball") < 0.6
    assert team_score("Emmen", "TV Möhlin") == 0.0


def test_score_game_swapped_sides() -> None:
    p = parse_name("CH_NLA_KriensLuzern_SuhrAarau_ca2018")
    g = {"homeTeamName": "HSC Suhr Aarau", "awayTeamName": "HC Kriens-Luzern"}
    assert 0.9 <= score_game(p, g) < 1.0


def test_league_filter() -> None:
    labels = {
        "Männer | Männer NLB": parse_name("CH_NLB_A_B_2022-09-11"),
        "SWISS Premium League | Frauen SPL2": parse_name("CH_Frauen_SPL2_A_B_2024-03-23"),
        "Mobiliar Handball Cup | Mobiliar Handball Cup Frauen": parse_name(
            "CH_Frauen_Cup_A_B_2024-04-27"),
        "Mobiliar Handball Cup | Schweizer SuperCup Männer": parse_name(
            "CH_Supercup_A_B_2023-08-20"),
    }
    for label, p in labels.items():
        assert any(r.search(label) for r in league_filter(p)), label
    assert not any(r.search("Mobiliar Handball Cup | Mobiliar Handball Cup Männer")
                   for r in league_filter(parse_name("CH_Frauen_Cup_A_B_2024-04-27")))


class _NoApi:
    def game(self, gid: int) -> dict[str, object]:
        return {"gameId": gid, "gameDateTime": "2024-03-23T18:00:00",
                "homeTeamName": "A", "awayTeamName": "B"}


def test_description_link_first_and_foreign() -> None:
    info = {"description": "Live: https://www.handball.ch/de/matchcenter/spiele/484345 viel Spass"}
    m = find_match(parse_name("CH_Frauen_SPL2_X_Y_2024-03-23"), _NoApi(), info)  # type: ignore[arg-type]
    assert isinstance(m, Match) and m.game and m.game["gameId"] == 484345
    assert m.method == "description link"
    m = find_match(parse_name("DE_3Liga_A_B_2024-01-01"), _NoApi(), None)  # type: ignore[arg-type]
    assert m.game is None and m.reason == "no handball.ch"
