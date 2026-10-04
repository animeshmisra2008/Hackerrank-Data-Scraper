# Hackerrank-Data-Scraper

Goal: fetch **public** HackerRank profile data (no auth) as a standalone
thing, later plug it into Student-Analytics (which currently only stores
`HackerRank_Username` + URL and shows "coming soon" in the profile tab).

Unofficial endpoints to try (from tashifkhan/hackerrank-stats-api):
- PROFILE: `/rest/contests/master/hackers/{u}/profile`
- SCORES: `/rest/hackers/{u}/scores_elo`
- BADGES: `/rest/hackers/{u}/badges`
- CONTESTS: `/rest/hackers/{u}/contest_participation`
- SUBMISSIONS: `/rest/hackers/{u}/submission_histories`
- RECENT: `/rest/hackers/{u}/recent_challenges`

Plan: raw client -> stable schema -> tiny FastAPI -> mocked tests.
