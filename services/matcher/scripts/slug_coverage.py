"""Does the program's SlugLock already prevent a duplicate room for every pair the matcher routes together?

For each pair of launches the matcher would route into one room (T3: folded symbol and folded name
equal; T2n: folded name equal, at least 4 characters), compute both launches' on-chain SlugLock
identity, `Launch::identity` = sha256(fold(symbol) || 0x00 || fold(name)) with the program's
ASCII-only `fold` (programs/doors_v1/src/state.rs; ported byte for byte in rules.program_fold and
checked against the SBF suite's reference vectors in tests/test_rules.py).

If both launches of a pair derive the same identity, the second `create_room` fails on-chain while
the first room is live, so no duplicate room can exist and the in-flight reservation only saves a
wasted transaction. If they differ, both rooms can be created and only the reservation (H-1)
prevents it.

Since the on-chain NameLock (H-1 closed), each pair also shows whether both launches carry the same
NameLock key (`rules.name_lock_key`, which `create_room` locks): if so, the second `create_room` fails
on-chain while the first room is live, whatever the SlugLocks say.

Usage: python3 scripts/slug_coverage.py [--json]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from matcher_service import rules  # noqa: E402

# (class, launch A (name, symbol), launch B (name, symbol))
PAIRS = [
    ("identical", ("Pepe", "PEPE"), ("Pepe", "PEPE")),
    ("ASCII case", ("Pepe", "PEPE"), ("PEPE", "pepe")),
    ("ASCII punctuation / $", ("Pepe!", "$PEPE"), ("Pepe", "PEPE")),
    ("ASCII digit look-alike", ("P3P3", "PEPE"), ("Pepe", "PEPE")),
    ("ASCII rn -> m", ("Doge Moon", "MOON"), ("Doge Rnoon", "MOON")),
    ("ASCII spacing", ("Dog Wif Hat", "WIF"), ("DogWifHat", "WIF")),
    ("stopword (COIN)", ("Pepe Coin", "PEPE"), ("Pepe", "PEPE")),
    ("stopword (THE / OFFICIAL)", ("The Official Pepe", "PEPE"), ("Pepe", "PEPE")),
    ("camelCase vs words", ("DogWifHat", "WIF"), ("dog wif hat", "WIF")),
    ("Cyrillic homoglyph", ("Pepe", "PEPE"), ("Реpe", "PEPE")),
    ("Greek homoglyph", ("Pepe", "PEPE"), ("Ρepe", "ΡEPE")),
    ("NFKC fullwidth", ("Pepe", "PEPE"), ("Ｐｅｐｅ", "ＰＥＰＥ")),
    ("zero-width space", ("Pepe", "PEPE"), ("Pe​pe", "PEPE")),
    ("T2n: same name, other symbol", ("Pepe", "PEPE"), ("Pepe", "FROG")),
    ("T2n: same name, symbol differs by one letter", ("Bonk Inu", "BONK"), ("Bonk Inu", "BONKI")),
    ("T2n: stopword + other symbol", ("Pepe Coin", "PEPE"), ("Pepe", "PEPE2")),
]


def row(cls, a, b):
    ca, cb = rules.ident(*a), rules.ident(*b)
    tier, _ = rules.text_tier(cb, ca)
    ia, ib = rules.program_identity(*a), rules.program_identity(*b)
    na, nb = rules.name_lock_key(*a), rules.name_lock_key(*b)
    return {"class": cls, "a": list(a), "b": list(b), "matcher_tier": tier,
            "routed_together": tier in rules.ROUTING_TIERS,
            "same_slug": ia == ib, "slug_a": ia.hex()[:16], "slug_b": ib.hex()[:16],
            "same_name_lock": na is not None and na == nb}


def main():
    rows = [row(*p) for p in PAIRS]
    if "--json" in sys.argv:
        print(json.dumps({"unicode": rules.UNICODE_VERSION, "rows": rows}, indent=2, ensure_ascii=False))
        return
    print("| class | launch A | launch B | matcher | same SlugLock? | same NameLock? |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        a, b = r["a"], r["b"]
        print(f"| {r['class']} | `{a[0]}` / `{a[1]}` | `{b[0]}` / `{b[1]}` | {r['matcher_tier']} | "
              f"{'yes' if r['same_slug'] else '**no**'} | {'yes' if r['same_name_lock'] else '**no**'} |")
    routed = [r for r in rows if r["routed_together"]]
    gaps = [r for r in routed if not r["same_slug"]]
    open_ = [r for r in routed if not (r["same_slug"] or r["same_name_lock"])]
    print(f"\n{len(gaps)} of {len(routed)} routed-together pairs derive different SlugLocks. With the NameLock, "
          f"{len(open_)} of {len(routed)} have no on-chain floor: the second create_room fails while the first "
          "room is live.")


if __name__ == "__main__":
    main()
