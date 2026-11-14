# The Commission Recount

Free, single-file commission audit tool from the **Build It With AI** YouTube series (Episode 29).

Open **index.html** in any browser (or use the live page). Paste one month of deals, your tier
settings, and what you actually paid each rep. It recomputes every commission with **marginal
tiers** — splits validated to 100%, pending deals set aside, refunds clawed back at the rep's
share — and shows exactly who was overpaid and who was shorted. Everything runs in your browser;
nothing is uploaded, nothing is stored.

## What's here
- `index.html` — the tool (single file, works offline)
- `SPEC.md` — the complete rule set the tool implements (the comp plan "law")
- `checker.py` — the independent Python referee, written from SPEC.md alone
- `PROMPTS.txt` / `prompts.html` — the three prompts exactly as sent
- `sample-data/` — Ironvale Garage Doors (fictional), one October: 73 deal rows, 5 reps
- `drafts/v1.html`, `drafts/v2.html` — the two real failed builds, kept as museum pieces.
  **They are labeled NOT THE TOOL for a reason. Do not use them.**

## Honest limits
It knows this one plan shape: marginal dollar tiers on monthly credit. Quotas, accelerators,
draws, SPIFs and cross-month clawbacks are out of scope. It can't know your plan's intent —
only the tiers you give it. Rows it cannot read are refused with a reason, never guessed.

All sample names and numbers are fictional.
