# hackerrank-fetcher

Small helper that fetches **public** HackerRank profile data.
Built to plug into `Student-Analytics` (which today only stores
`HackerRank_Username` + `HackerRank_URL` and shows "coming soon" in the profile
tab). Lazy by design: fetch one user when their profile opens, never a big
batch at once. No login, no secrets.

Unofficial endpoints used (proven, from `tashifkhan/hackerrank-stats-api`):

| Kind | URL |
|---|---|
| PROFILE | `/rest/contests/master/hackers/{u}/profile` → `model` |
| SCORES | `/rest/hackers/{u}/scores_elo` → list |
| BADGES | `/rest/hackers/{u}/badges` → `models[]` |
| CONTESTS | `/rest/hackers/{u}/contest_participation?offset=0&limit=50` |
| RATINGS | `/rest/hackers/{u}/rating_histories_elo` |
| SUBMISSIONS | `/rest/hackers/{u}/submission_histories` |
| RECENT | `/rest/hackers/{u}/recent_challenges?limit=100&response_version=v2` (page by page, max 25 pages) |

Browser headers, 20s timeout, answers remembered for 1 hour.

## Files

```text
src/hackerrank_client/client.py   # talks to HackerRank (7 fetches)
src/hackerrank_client/service.py  # fetches everything at once, cleans it up
src/hackerrank_client/schemas.py  # our clean data format
src/hackerrank_client/cache.py    # remembers answers for 1 hour (no Redis)
api.py                            # website: /{username}/profile | /badges | /contests | /heatmap
tests/                            # tests with fake answers (no internet needed)
```

## Clean format

Only these keys are ever returned — HackerRank's messy keys
(`badge_type`, `track_id`, `hacker_rank`, `ch_slug`, …) never leak out:

```json
{
  "username": "shashank21j",
  "display_name": "Shashank Sharma",
  "badges": [{"track": "Problem Solving", "stars": 6, "solved": 202}],
  "practice_score": 8803,
  "total_solved": 202,
  "contests": [{"name": "Weekly Challenges - Week 4", "slug": "w4"}]
}
```

`practice_score` adds up points from every topic.
`total_solved` uses the Problem Solving badge (else adds everything up).

## Run

```bash
pip install -r requirements.txt
python -m uvicorn api:app --reload --port 8000
```

## Try it

```bash
curl.exe http://localhost:8000/health
curl.exe http://localhost:8000/shashank21j/profile
curl.exe http://localhost:8000/shashank21j/badges
curl.exe http://localhost:8000/shashank21j/contests   # new, thin data
curl.exe http://localhost:8000/shashank21j/heatmap    # new, thin data
```

Errors are simple JSON: unknown user → `404 {"error":"user_not_found"}`,
HackerRank broken → `502 {"error":"upstream_error"}`.
Badges/activity/recent give empty defaults for quiet accounts instead of errors.

## Use it in Python

```python
import asyncio
from hackerrank_client import HackerRankAPI, get_full_profile

async def main():
    api = HackerRankAPI()
    try:
        print((await get_full_profile("shashank21j", api)).to_dict())
    finally:
        await api.close()

asyncio.run(main())
```

## Tests

```bash
python -m pytest tests/ -q
```

Fake HackerRank answers — no internet. Covers unknown users, empty history,
broken answers, and the 25-page guard on recent challenges.

## Limits (read before trusting the numbers)

- **Unofficial pages** — HackerRank can change or block them anytime; we show
  empty sections / `upstream_error` instead of retrying forever.
- **No worldwide rank** — HackerRank only gives per-topic ranks, so there is
  no single global rank number to show.
- **Empty history is normal** — new/quiet accounts return no activity and no
  badges; that shows as "no data", not an error.
- **Totals are estimates** — points/solved are added up by us, not official totals.
- **`/contests` + `/heatmap` are new** — upstream data is thin
  (name/slug, date→count). `/profile` + `/badges` are the solid ones.
- No Redis/Docker — memory cache only (1 hour).
