# 015. Insight engine and LLM text generation

- Status: accepted
- Date: 2026-11-03

## Context
BRIEF 4.9 asks for automatic insights with a text generator. Coaches act on these statements, so a wrong
number or an invented pattern costs trust immediately. Youth teams make player data sensitive.

## Decision
- **Insights are computed, not generated.** `handball_metrics.insights` holds a catalogue of rules
  (shooting, saves, turnovers, 7 m, zones, conceded goal zone, fast breaks, powerplay, droughts, runs,
  goalkeepers via GSAx, players). Rates are compared with 90 % Wilson intervals against the other matches of
  the season; each rule has a minimum sample. Every insight carries its parameters, sample size and an event
  filter, so each statement opens the events behind it. The UI renders localized templates.
- **The LLM only rewords.** An optional summary (`POST /matches/{id}/summary`, staff) sends the ranked
  insights as facts to the Claude API (`claude-opus-5-5`, effort low, server-side fallbacks on policy
  declines). Facts contain no names or ids, players appear as jersey numbers. The response is accepted only if
  every number in it appears in the facts (`numbers_ok`); otherwise it is rejected and the templates stay.
  The summary is stored with a fingerprint of the insights and hidden as soon as they change.
- Without `HB_ANTHROPIC_API_KEY` everything works on templates; the button explains that text generation is
  not configured.

## Consequences
- Insight quality is bounded by tagging quality; the minimum samples keep small matches silent.
- The number check is strict (it also rejects correct paraphrases such as "zwei Drittel"); that is intended.
- Cost per summary is a single short request on demand, no background generation.
