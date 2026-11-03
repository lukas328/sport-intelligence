# Load test M9

Date: 2026-11-03 · Script: `tests/load/run.py` · Target (BRIEF 7.3): read p95 < 300 ms

Setup: whole stack in Docker Compose on one 4 vCPU / 16 GB machine; the load generator, Postgres,
Redis, SeaweedFS and both workers share these cores. One club, 10 matches with 60 tagged events each.
Mix of the hot read paths: match, events, stats, insights, season stats, notifications, playlists,
plays, match list. Open loop (Poisson arrivals) so queueing shows up honestly.

## Findings and fixes (profiling before optimising)
1. **Bug:** concurrent first views of a match raced on inserting the stats cache (unique key, HTTP 500
   under load). Fixed with an atomic `INSERT ... ON CONFLICT DO UPDATE`; regression test added.
2. **One API process** used one of four cores (49 rps, p50 750 ms closed loop). Now one Uvicorn worker
   per core (`HB_WORKERS`, default min(4, cores)): 136 rps closed loop, no errors.
3. **Insights and season stats** read the cached stats of every match of the season per request
   (p95 1.1 to 1.3 s at 100 rps). Now cached as a whole, keyed by one aggregated version query over the
   season's matches and events: p95 47 ms at 100 rps.
4. Per request the API runs 5 queries (session, organisation, memberships, team, data) plus the tenant
   settings; no N+1 found on the measured paths.

## Results after the fixes
### 50 requests per second
```
users=50 seconds=60 requests=2841 rps=47
endpoint            n     p50     p95     p99   err
match             279      21      33     458     0
events            312      22      34      83     0
stats             319      22      43     325     0
insights          307      22      34      90     0
season            321      22      38     853     0
notifications     330      20      36     221     0
playlists         303      19      32      80     0
plays             332      19      40     366     0
matches           338      20      30      65     0
error rate 0.00%, worst p95 43 ms (budget 300 ms)
```

### 100 requests per second
```
users=50 seconds=60 requests=5596 rps=93
endpoint            n     p50     p95     p99   err
match             635      21      39      57     0
events            595      22      50      71     0
stats             587      21      43      70     0
insights          632      22      47      84     0
season            613      22      46      72     0
notifications     603      19      40      73     0
playlists         649      19      36      65     0
plays             678      19      37      54     0
matches           604      20      40      60     0
error rate 0.00%, worst p95 50 ms (budget 300 ms)
```

### 200 requests per second (saturation)
```
users=50 seconds=60 requests=7382 rps=123
endpoint            n     p50     p95     p99   err
match             842     114    2414    3327     0
events            760     249    2386    3276     0
stats             869     190    2439    3384     0
insights          788     130    2564    4404     0
season            817     138    2258    3392     0
notifications     847     162    2185    3580     0
playlists         846     131    2256    3045     0
plays             812     140    2294    3016     0
matches           801      90    2403    3031     1
error rate 0.01%, worst p95 2564 ms (budget 300 ms)
```

## Interpretation
- The budget holds up to about **100 requests per second** on this single shared machine. With a
  typical 10 s think time that is roughly 1000 people clicking through matches at the same moment,
  far above the expected peak (Sunday evening after matchdays).
- At 200 requests per second the machine saturates at about 120 requests per second (the load
  generator itself takes a core). The API is stateless: production scales horizontally behind the
  load balancer, Postgres connections stay bounded by `pool_size` per worker.
- Not covered here: uploads (bandwidth bound, direct to object storage) and SSE streams (one idle
  connection per open match page).

Rerun: `uv run python tests/load/run.py --rate 100 --seconds 60` against a running stack.
