"""Generate synthetic GL and bank CSVs with injected breaks (seeded, repeatable)."""
import csv, random, sys
from datetime import date, timedelta

ACCOUNTS = ["Cash & Bank", "Receivables", "Payables", "Trading Revenue", "Fees & Commissions", "FX Revaluation"]

def main(n=500, seed=42, out="sample_data"):
    rnd = random.Random(seed)
    gl, bank = [], []
    for i in range(1, n + 1):
        ref = f"TXN{i:05d}"
        amt = round(rnd.uniform(500, 90500), 2)
        d = (date(2026, 9, 1) + timedelta(days=rnd.randint(0, 27))).isoformat()
        acc = rnd.choice(ACCOUNTS)
        g = [ref, d, acc, amt]
        b = [ref, d, acc, amt]
        x = rnd.random()
        if x < 0.05:                                   # amount mismatch
            delta = rnd.uniform(0.5, 50) if rnd.random() < 0.5 else rnd.uniform(0.5, 2000)
            b[3] = round(amt + rnd.choice([-1, 1]) * delta, 2)
        if 0.08 <= x < 0.10:                           # missing in GL
            bank.append(b)
        else:
            gl.append(g)
            if not (0.05 <= x < 0.08):                 # missing in bank
                bank.append(b)
            if 0.10 <= x < 0.12:                       # duplicate GL posting
                gl.append(list(g))
    for name, data in (("gl.csv", gl), ("bank.csv", bank)):
        with open(f"{out}/{name}", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ref", "date", "account", "amount"])
            w.writerows(data)
    print(f"Wrote {len(gl)} GL rows and {len(bank)} bank rows to {out}/")

if __name__ == "__main__":
    main(*(int(a) for a in sys.argv[1:3]))
