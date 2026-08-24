# BLEAK — B + LEAK

Public leak blotter. OOF was the docket. This is the dump.

Live: **https://sambas123.github.io/thats-bleak/**

The page answers **so what?**: Have I Been Pwned is a catalog, not a rumor; not every leak is a hack (CyberLeek’s token traded before the GTA footage); we do not host files or footage. The useful signal is whether new catalog rows and leak headlines are still landing.

Unofficial. Not affiliated with HIBP, Rockstar, or Take-Two. Not a pirate bay. Not legal advice.

The ticker is **$BLEAK**. The letters are the product: B + LEAK, counted in public.

## What it counts

| Field | Source | Notes |
|---|---|---|
| Accounts in 2026-dated breaches | [Have I Been Pwned](https://haveibeenpwned.com/api/v3/breaches) | sum of `PwnCount` where `BreachDate` starts with 2026 |
| Breaches dated 2026 / added 7d | same | `AddedDate` is when it hit the catalog |
| Headlines, 7 days | Google News RSS | CyberLeek, GTA 6 leak, data breach / data leak |
| On-the-record chips | Hand-cited news | see `scripts/refresh_tape.py` → `RECORD` |

We do not download dumps. We do not embed unreleased game footage. CyberLeek is on the tape as reporting (token-first leak), not as clips.

## How it updates

GitHub Action, about once an hour (`scripts/refresh_tape.py` → `tape.json`). If a source fails, the last good slice stays.

One HIBP catalog pull per hour. Do not turn this into a live proxy.

## Run locally

```bash
python3 scripts/refresh_tape.py
python3 -m http.server 8767
# open http://127.0.0.1:8767
```

## After a ticker exists

Set `token` in `tape.json` (the refresh script preserves it):

```json
"token": { "symbol": "BLEAK", "mint": "<address>" }
```

Sister page: [OOF](https://sambas123.github.io/thats-weird/).
