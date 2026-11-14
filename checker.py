#!/usr/bin/env python3
"""Independent referee for The Commission Recount, written from SPEC.md only.
Exact arithmetic with fractions.Fraction; cents rounded half-up (away from zero) once."""
import sys, json, re
from fractions import Fraction

def parse_csv(text):
    rows, row, field, inq = [], [], [], False
    s = text or ""
    i = 0
    while i < len(s):
        c = s[i]
        if inq:
            if c == '"':
                if i + 1 < len(s) and s[i+1] == '"': field.append('"'); i += 1
                else: inq = False
            else: field.append(c)
        elif c == '"': inq = True
        elif c == ',': row.append(''.join(field)); field = []
        elif c == '\n': row.append(''.join(field)); rows.append(row); row = []; field = []
        elif c == '\r': pass
        else: field.append(c)
        i += 1
    row.append(''.join(field))
    if len(row) > 1 or row[0].strip() != "": rows.append(row)
    return [r for r in rows if any(str(x).strip() != "" for x in r)]

DEC = re.compile(r'^(\d+(\.\d*)?|\.\d+)$')
def parse_dec(raw, allow_neg=False):
    if raw is None: return None
    s = re.sub(r'[$,\s]', '', str(raw).strip())
    if s == "": return None
    neg = False
    if allow_neg and s[:1] in "+-":
        neg = s[0] == '-'; s = s[1:]
    if not DEC.match(s): return None
    v = Fraction(s)
    return -v if neg else v

def cents(v):  # Fraction -> int cents, half up away from zero
    neg = v < 0
    n = -v if neg else v
    n100 = n * 100
    q = n100.numerator // n100.denominator
    r = n100 - q
    if r * 2 >= 1: q += 1
    return -q if neg else q

def cstr(c):
    neg = c < 0
    c = -c if neg else c
    return ("-" if neg else "") + f"{c//100}.{c%100:02d}"

def header_index(row):
    return {str(h).strip().lower(): i for i, h in enumerate(row)}

def run(deals_text, paid_text, settings_text):
    banner_reasons, refusals = [], []
    defaults = {"tier1_up_to": "40000", "tier1_rate": "4", "tier2_up_to": "80000",
                "tier2_rate": "6", "tier3_rate": "8"}
    set_vals, settings_invalid = {}, False
    srows = parse_csv(settings_text or "")
    if srows:
        h = header_index(srows[0])
        if "setting" not in h or "value" not in h: settings_invalid = True
        else:
            for r in srows[1:]:
                name = (r[h["setting"]] if h["setting"] < len(r) else "").strip().lower()
                if name not in defaults: continue
                v = parse_dec(r[h["value"]] if h["value"] < len(r) else None)
                if v is None: settings_invalid = True; break
                set_vals[name] = v
    tiers = {}
    if not settings_invalid:
        for k, d in defaults.items():
            tiers[k] = set_vals.get(k, Fraction(d))
        if not (tiers["tier1_up_to"] < tiers["tier2_up_to"]) or tiers["tier1_up_to"] <= 0 \
           or tiers["tier2_up_to"] <= 0 or tiers["tier1_rate"] < 0 or tiers["tier2_rate"] < 0 \
           or tiers["tier3_rate"] < 0:
            settings_invalid = True
    if settings_invalid: banner_reasons.append("settings invalid")

    drows = parse_csv(deals_text or "")
    rows_in, checked, set_aside = 0, [], []
    deals_header_ok = False
    if drows:
        h = header_index(drows[0])
        if all(k in h for k in ("deal", "rep", "amount", "status")):
            deals_header_ok = True
            share_i = h.get("share %")
            parsed = []
            for r in drows[1:]:
                rows_in += 1
                g = lambda i: (r[i] if i is not None and i < len(r) else "")
                deal = str(g(h["deal"])).strip(); rep = str(g(h["rep"])).strip()
                status = str(g(h["status"])).strip().lower()
                raw_share = str(g(share_i)).strip() if share_i is not None else ""
                if deal == "": refusals.append(("(blank)", rep or "(blank)", "missing deal id")); continue
                if rep == "": refusals.append((deal, "(blank)", "missing rep")); continue
                amount = parse_dec(g(h["amount"]))
                if amount is None: refusals.append((deal, rep, "unreadable amount")); continue
                if status not in ("collected", "pending", "refunded"):
                    refusals.append((deal, rep, "unknown status")); continue
                if raw_share == "": share = Fraction(100)
                else:
                    share = parse_dec(raw_share)
                    if share is None or not (0 < share <= 100):
                        refusals.append((deal, rep, "unreadable share")); continue
                parsed.append((deal, rep, amount, status, share))
            by_deal = {}
            for p in parsed: by_deal.setdefault(p[0], []).append(p)
            for deal, rows in by_deal.items():
                reason = None
                seen = set()
                for p in rows:
                    if p[1] in seen: reason = "duplicate deal row"; break
                    seen.add(p[1])
                if not reason and any(p[2] != rows[0][2] for p in rows): reason = "conflicting amounts"
                if not reason and any(p[3] != rows[0][3] for p in rows): reason = "conflicting statuses"
                if not reason and sum(p[4] for p in rows) != 100: reason = "shares do not total 100"
                if reason:
                    for p in rows: refusals.append((deal, p[1], reason))
                else:
                    for p in rows: (set_aside if p[3] == "pending" else checked).append(p)
        else: banner_reasons.append("header row unreadable: Deals")
    else: banner_reasons.append("header row unreadable: Deals")

    prows = parse_csv(paid_text or "")
    paid_by = {}
    if prows:
        h = header_index(prows[0])
        if "rep" in h and "paid" in h:
            for r in prows[1:]:
                rep = (r[h["rep"]] if h["rep"] < len(r) else "").strip()
                if rep == "": refusals.append(("(paid)", "(blank)", "missing rep")); continue
                v = parse_dec(r[h["paid"]] if h["paid"] < len(r) else None, allow_neg=True)
                if v is None: refusals.append(("(paid)", rep, "unreadable paid amount")); continue
                paid_by[rep] = paid_by.get(rep, Fraction(0)) + v
        else: banner_reasons.append("header row unreadable: Paid")
    else: banner_reasons.append("header row unreadable: Paid")

    credit_by = {}
    for deal, rep, amount, status, share in checked:
        contrib = amount * share / 100
        credit_by[rep] = credit_by.get(rep, Fraction(0)) + (-contrib if status == "refunded" else contrib)

    def commission(C):
        if settings_invalid or C <= 0: return Fraction(0)
        t1, t2 = tiers["tier1_up_to"], tiers["tier2_up_to"]
        b1 = min(C, t1)
        b2 = min(max(C - t1, 0), t2 - t1)
        b3 = max(C - t2, 0)
        c = b1 * tiers["tier1_rate"] / 100 + b2 * tiers["tier2_rate"] / 100 + b3 * tiers["tier3_rate"] / 100
        return max(c, Fraction(0))

    reps = []
    for rep in set(credit_by) | set(paid_by):
        C = credit_by.get(rep, Fraction(0))
        due_c = cents(commission(C))
        has_paid = rep in paid_by
        paid_c = cents(paid_by[rep]) if has_paid else None
        delta_c = (paid_c - due_c) if has_paid else None
        reps.append({"rep": rep, "credit": cstr(cents(C)), "commission": cstr(due_c),
                     "paid": cstr(paid_c) if has_paid else None,
                     "delta": cstr(delta_c) if has_paid else None,
                     "_abs": -1 if delta_c is None else abs(delta_c)})
    reps.sort(key=lambda r: (-r["_abs"], r["rep"]))
    for r in reps: del r["_abs"]

    def cents_of(s):
        neg = s.startswith("-"); t = s[1:] if neg else s
        w, f = t.split("."); c = int(w) * 100 + int(f)
        return -c if neg else c
    due_t = sum(cents_of(r["commission"]) for r in reps)
    paid_t = sum(cents_of(r["paid"]) for r in reps if r["paid"] is not None)
    over_t = sum(cents_of(r["delta"]) for r in reps if r["delta"] is not None and cents_of(r["delta"]) > 0)
    under_t = -sum(cents_of(r["delta"]) for r in reps if r["delta"] is not None and cents_of(r["delta"]) < 0)

    cross = Fraction(0)
    for deal, rep, amount, status, share in checked:
        contrib = amount * share / 100
        cross += -contrib if status == "refunded" else contrib
    if cents(cross) != cents(sum(credit_by.values(), Fraction(0))):
        banner_reasons.append("money cross-foot failed")
    deal_refused = sum(1 for r in refusals if r[0] != "(paid)")
    if deals_header_ok and rows_in != len(checked) + len(set_aside) + deal_refused:
        banner_reasons.append("row count arithmetic failed")
    if deals_header_ok and rows_in > 0 and deal_refused * 10 > rows_in:
        banner_reasons.append("more than 10% of rows refused")

    banner = len(banner_reasons) > 0
    def rate_str(f):
        neg = f < 0; n = -f if neg else f
        n4 = n * 10000
        q = n4.numerator // n4.denominator
        if (n4 - q) * 2 >= 1: q += 1
        s = ("-" if neg else "") + f"{q//10000}.{q%10000:04d}"
        return re.sub(r'\.?0+$', '', s)
    return {
        "banner": banner,
        "bannerText": "DO NOT TRUST THIS RECOUNT" if banner else "",
        "bannerReasons": sorted(banner_reasons),
        "counts": {"rowsIn": rows_in, "checked": len(checked), "setAside": len(set_aside), "refused": deal_refused},
        "reps": [] if banner else reps,
        "totals": None if banner else {"due": cstr(due_t), "paid": cstr(paid_t), "over": cstr(over_t), "under": cstr(under_t)},
        "setAside": [] if banner else sorted(
            [{"deal": d, "rep": rp, "value": cstr(cents(a * sh / 100))} for d, rp, a, st, sh in set_aside],
            key=lambda x: (x["deal"], x["rep"])),
        "refusals": [{"deal": d, "rep": rp, "reason": rs} for d, rp, rs in
                     sorted(refusals, key=lambda x: (x[0], x[1], x[2]))],
        "tiers": None if settings_invalid else {
            "tier1_up_to": cstr(cents(tiers["tier1_up_to"])), "tier1_rate": rate_str(tiers["tier1_rate"]),
            "tier2_up_to": cstr(cents(tiers["tier2_up_to"])), "tier2_rate": rate_str(tiers["tier2_rate"]),
            "tier3_rate": rate_str(tiers["tier3_rate"])},
    }

if __name__ == "__main__":
    deals = open(sys.argv[1]).read()
    paid = open(sys.argv[2]).read()
    settings = open(sys.argv[3]).read() if len(sys.argv) > 3 else ""
    print(json.dumps(run(deals, paid, settings), indent=1, sort_keys=True))
