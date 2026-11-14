# The Commission Recount — SPEC (the law)
The tool recomputes one month of sales commissions from the shop's own comp plan and compares
them to what was actually paid. Everything below is the complete rule set; the Python checker
is written from THIS FILE ONLY, blind to the JavaScript.

## Inputs
Three pastes (CSV, first row = headers; columns found BY HEADER NAME, any order, case-insensitive,
surrounding whitespace ignored; a quoted field may contain commas):

### 1. Deals — one row per rep-credit on a deal
Headers (required unless marked): `Deal`, `Rep`, `Amount`, `Status`, `Share %` (optional column).
- `Deal`: the deal id (non-empty string).
- `Rep`: the credited rep's name (non-empty string).
- `Amount`: the deal's full dollar amount. Parse: strip `$`, commas and whitespace; the rest must
  be a plain non-negative decimal number (digits with at most one `.`). Anything else (letters,
  empty, negative) → the ROW is refused with reason `unreadable amount`.
- `Status`: one of `collected`, `pending`, `refunded` (case-insensitive). Any other value → the
  row is refused with reason `unknown status`.
- `Share %`: that rep's credit share of the deal, 0 < share ≤ 100, plain decimal (a missing
  column or an empty cell means 100). Unparseable or out of range → row refused, `unreadable share`.

A deal split between reps appears as several rows with the SAME deal id (each row its own rep and
share). Grouping is by deal id.

### 2. Paid — what the owner actually paid each rep for the month
Headers: `Rep`, `Paid`. `Paid` parses like Amount but may be negative (a recovery). Unreadable →
that PAID row is refused (reason `unreadable paid amount`); the rep is still recomputed and the
comparison column shows `no payment row`. Several Paid rows for one rep are summed. A Paid row
with an empty Rep is refused (`missing rep`).

### 3. Settings (optional; defaults in parentheses)
CSV with headers `Setting`, `Value`; one setting per row. Known settings:
`tier1_up_to` (40000), `tier1_rate` (4), `tier2_up_to` (80000), `tier2_rate` (6), `tier3_rate` (8).
All plain decimals; rates are percent. Unknown setting names are ignored; absent settings take the
defaults. `tier1_up_to` must be < `tier2_up_to`, both > 0, rates ≥ 0; an unparseable Value or a
violated constraint makes Settings invalid → the whole run fails the audit (banner, nothing
computed).

## Validation and refusals (deal rows)
Row-level refusals: `unreadable amount`, `unknown status`, `unreadable share`, missing/empty `Deal`
or `Rep` (`missing deal id` / `missing rep`).
Deal-level refusals (applied to every remaining row of that deal, after row-level refusals):
- `duplicate deal row`: two rows share the same deal id AND the same rep. (All rows of that deal
  are refused.)
- `conflicting amounts`: rows of one deal disagree on Amount (exact string-parsed value compare).
- `conflicting statuses`: rows of one deal disagree on Status.
- `shares do not total 100`: the sum of shares of a deal's rows ≠ 100 exactly (after decimal
  parse; tolerance 0 — the plan says shares must total exactly 100).
A refusal names the row (deal id + rep when known) and the reason, verbatim as above.

## Counting (public arithmetic)
`deal rows in = checked + set aside + refused` — rows, not deals.
- refused: rows refused above.
- set aside: surviving rows whose Status is `pending` (sold, not collected — worth nothing yet).
- checked: surviving `collected` and `refunded` rows.

## Credit
Per rep: credit = Σ over their checked rows of `amount × share/100`, where `refunded` rows
SUBTRACT (clawback at the same share) and `collected` rows add. Exact decimal arithmetic;
credit is rounded to the cent (half up) only after the sum.
If a rep's credit is negative, commission for the month is $0 (no cross-month carry; the negative
credit is reported as-is).

## Commission (MARGINAL tiers on monthly credit)
With credit C (in dollars, at full precision before the cent-rounding of the credit display —
commission is computed from the exact credit sum, then rounded to the cent, half up, ONCE):
- band 1: min(C, tier1_up_to) × tier1_rate% — "up to and including tier1_up_to".
- band 2: min(max(C − tier1_up_to, 0), tier2_up_to − tier1_up_to) × tier2_rate%.
- band 3: max(C − tier2_up_to, 0) × tier3_rate%.
Commission = band1 + band2 + band3, floored at 0 (negative credit ⇒ 0).
A credit EXACTLY equal to tier1_up_to lies entirely in band 1 (the boundary dollar does not
touch band 2). Rates apply only to the dollars inside their band — never to the whole credit.

## Comparison
Per rep (union of reps in Deals-surviving rows and Paid rows): correct commission, paid
(0-default only if the rep has a Paid row that parsed; otherwise `no payment row`), delta =
paid − correct ( + = overpaid, − = underpaid). Reps in Paid but not in Deals are listed with
credit 0, commission 0.

## Audit (self-check; failure ⇒ banner)
The report opens with `DO NOT TRUST THIS RECOUNT` in red when ANY of:
- a required header is missing in Deals or Paid (named: `header row unreadable: <table>`);
- row count arithmetic fails (in ≠ checked + set aside + refused);
- the money cross-foot fails: Σ per-rep credit ≠ Σ per-deal-row signed credited amounts
  (recomputed independently, compared to the cent);
- more than 10% of deal rows are refused;
- Settings invalid (above).
The banner page still lists refusals, but prices nothing.

## Outputs (the report)
1. Audit line + counts: rows in, checked, set aside, refused.
2. Per-rep table: credit, commission due, paid, delta (sorted by |delta| descending).
3. Totals: total commission due, total paid, total overpaid (Σ positive deltas), total
   underpaid (Σ negative deltas, shown positive).
4. Set-aside list (pending rows: deal, rep, amount × share).
5. Refusals (row + verbatim reason).
6. Tier recap: the three bands and rates used.
No network, no persistence: the page makes zero external requests and stores nothing.
