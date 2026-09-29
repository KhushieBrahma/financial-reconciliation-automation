"""Reconcile a GL extract against a bank feed and write an exception report.

Usage: python python/reconcile.py sample_data/gl.csv sample_data/bank.csv [tolerance] [high_threshold]
"""
import csv, sys
from collections import defaultdict

def load(path):
    with open(path, newline="") as f:
        return [dict(ref=r["ref"], date=r["date"], account=r["account"], amount=float(r["amount"]))
                for r in csv.DictReader(f)]

def cause(kind, var):
    if kind == "Amount":
        return ("Small difference: likely rounding, FX or bank-charge netting" if abs(var) <= 100
                else "Large difference: check keying error or partial settlement")
    return {"MissingBank": "Not on bank feed: likely timing/cut-off or unsettled item",
            "MissingGL": "On bank, not booked: likely unposted receipt or missing journal",
            "Duplicate": "Posted twice in GL: likely duplicate upload or re-run of a batch"}[kind]

def severity(var, high):
    v = abs(var)
    return "High" if v >= high else "Medium" if v >= high / 10 else "Low"

def reconcile(gl, bank, tol=1.0, high=10000.0):
    bank_by_ref = {b["ref"]: b for b in bank}
    seen, breaks = set(), []
    for g in gl:
        if g["ref"] in seen:
            breaks.append((g, g["amount"], None, g["amount"], "Duplicate")); continue
        seen.add(g["ref"])
        b = bank_by_ref.get(g["ref"])
        if b is None:
            breaks.append((g, g["amount"], None, g["amount"], "MissingBank")); continue
        var = round(g["amount"] - b["amount"], 2)
        if abs(var) > tol:
            breaks.append((g, g["amount"], b["amount"], var, "Amount"))
    for b in bank:
        if b["ref"] not in seen:
            breaks.append((b, None, b["amount"], -b["amount"], "MissingGL"))
    rows = [dict(ref=r["ref"], date=r["date"], account=r["account"], gl=g, bank=bk, variance=v,
                 break_type=k, severity=severity(v, high), likely_cause=cause(k, v), status="Open")
            for r, g, bk, v, k in breaks]
    return sorted(rows, key=lambda x: abs(x["variance"]), reverse=True)

def main():
    gl_path, bank_path = sys.argv[1], sys.argv[2]
    tol = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    high = float(sys.argv[4]) if len(sys.argv) > 4 else 10000.0
    gl, bank = load(gl_path), load(bank_path)
    rows = reconcile(gl, bank, tol, high)
    total = len({g["ref"] for g in gl})
    breaking = len({r["ref"] for r in rows})
    print(f"GL rows: {len(gl)} | Bank rows: {len(bank)} | Match rate: {(total - breaking) / total:.1%}")
    print(f"Breaks: {len(rows)} | Net variance: {sum(r['variance'] for r in rows):,.2f} | "
          f"Gross variance: {sum(abs(r['variance']) for r in rows):,.2f}")
    by_type, by_acc = defaultdict(int), defaultdict(float)
    for r in rows:
        by_type[r["break_type"]] += 1; by_acc[r["account"]] += abs(r["variance"])
    print("By type:", dict(by_type))
    print("Gross variance by account:", {k: round(v, 2) for k, v in by_acc.items()})
    with open("exception_report.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print("Wrote exception_report.csv")

if __name__ == "__main__":
    main()
