"""pHash robustness and false-match rate on a real image corpus (Twemoji PNGs from emoji-datasource-twitter).

Why this corpus: pump.fun token images could not be fetched from this environment (the metadata/image hosts are
denied by the network policy; ipfs.io answers 429). Twemoji are real, flat, cartoon-style images, closer to memecoin
logos than photographs. They are 64x64 sources, upscaled here to 256x256 before editing.

Positives: each sampled base image vs. edited copies of itself (recolour, crop, rescale, re-encode, light edits).
Negatives: every pair of distinct base emoji (skin-tone variants and the Component category excluded).

Usage: python3 image_robustness.py <package_dir> <out.md> [n_positive_sample]
"""
import io
import json
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(__file__))
from phash import flatten_alpha, phash_bits, phash_hex  # noqa: E402

SEED = 20261031
THRESHOLDS = [4, 6, 8, 10, 12, 14, 16, 18, 20]


def hue_rotate(img, deg):
    h, s, v = img.convert("HSV").split()
    h = h.point(lambda x: (x + int(round(deg / 360 * 256))) % 256)
    return Image.merge("HSV", (h, s, v)).convert("RGB")


def crop_centre(img, frac):
    w, h = img.size
    dx, dy = int(w * frac / 2), int(h * frac / 2)
    return img.crop((dx, dy, w - dx, h - dy))


def crop_corner(img, frac):
    w, h = img.size
    return img.crop((int(w * frac), int(h * frac), w, h))


def jpeg(img, q):
    b = io.BytesIO()
    img.save(b, "JPEG", quality=q)
    b.seek(0)
    return Image.open(b).convert("RGB")


def caption(img):
    img = img.copy()
    w, h = img.size
    d = ImageDraw.Draw(img)
    d.rectangle((0, int(h * 0.85), w, h), fill=(0, 0, 0))
    d.text((int(w * 0.05), int(h * 0.88)), "$TICKER TO THE MOON", fill=(255, 255, 255))
    return img


def sticker(img, other):
    img = img.copy()
    w, h = img.size
    s = other.resize((w // 4, h // 4), Image.Resampling.LANCZOS)
    img.paste(s, (w - w // 4 - 4, 4))
    return img


def noise(img, sigma, rng):
    a = np.asarray(img, dtype=np.float64)
    a = a + np.random.default_rng(rng.randrange(1 << 30)).normal(0, sigma, a.shape)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def transforms(img, other, rng):
    return {
        "re-encode JPEG q85": jpeg(img, 85),
        "JPEG q40": jpeg(img, 40),
        "rescale to 128 px": img.resize((128, 128), Image.Resampling.BILINEAR),
        "rescale to 512 px": img.resize((512, 512), Image.Resampling.BICUBIC),
        "non-square stretch 256x200": img.resize((256, 200), Image.Resampling.BILINEAR),
        "centre crop 5%": crop_centre(img, 0.05),
        "centre crop 10%": crop_centre(img, 0.10),
        "centre crop 20%": crop_centre(img, 0.20),
        "corner crop 10%": crop_corner(img, 0.10),
        "hue rotate 60 deg": hue_rotate(img, 60),
        "hue rotate 180 deg": hue_rotate(img, 180),
        "grayscale": ImageOps.grayscale(img).convert("RGB"),
        "saturation x1.6": ImageEnhance.Color(img).enhance(1.6),
        "brightness x0.8": ImageEnhance.Brightness(img).enhance(0.8),
        "brightness x1.2": ImageEnhance.Brightness(img).enhance(1.2),
        "contrast x1.3": ImageEnhance.Contrast(img).enhance(1.3),
        "gaussian blur r=1.5": img.filter(ImageFilter.GaussianBlur(1.5)),
        "noise sigma 12": noise(img, 12, rng),
        "8 px border": ImageOps.expand(img, border=8, fill=(255, 215, 0)),
        "caption bar (bottom 15%)": caption(img),
        "sticker in corner (1/16 area)": sticker(img, other),
        "rotate 5 deg": img.rotate(5, resample=Image.Resampling.BICUBIC, fillcolor=(255, 255, 255)),
        "combo: crop 10% + hue 60 + caption + JPEG q60": jpeg(caption(hue_rotate(crop_centre(img, 0.10), 60)), 60),
        "mirror (left-right)": ImageOps.mirror(img),
        "colour invert": ImageOps.invert(img),
    }


def load(pkg, fname):
    with Image.open(os.path.join(pkg, "img", "twitter", "64", fname)) as im:
        return flatten_alpha(im).resize((256, 256), Image.Resampling.LANCZOS)


def main():
    pkg, out = sys.argv[1], sys.argv[2]
    n_pos = int(sys.argv[3]) if len(sys.argv) > 3 else 400
    meta = json.load(open(os.path.join(pkg, "emoji.json")))
    version = json.load(open(os.path.join(pkg, "package.json")))["version"]
    base = [(e["image"], e["category"]) for e in meta
            if e.get("has_img_twitter") and e["category"] != "Component"
            and os.path.exists(os.path.join(pkg, "img", "twitter", "64", e["image"]))]
    base.sort()
    rng = random.Random(SEED)

    # negatives: all distinct pairs
    bits = np.array([phash_bits(load(pkg, f)).flatten() for f, _ in base], dtype=np.uint8)
    hexes = [phash_hex(load(pkg, f)) for f, _ in base[:5]]
    is_flag = np.array([c == "Flags" for _, c in base])
    packed = np.packbits(bits, axis=1)  # n x 8 bytes
    pop = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)
    n = len(base)
    hist_all = np.zeros(65, dtype=np.int64)
    hist_noflag = np.zeros(65, dtype=np.int64)
    nearest = np.full(n, 64)
    for i in range(n - 1):
        d = pop[np.bitwise_xor(packed[i + 1:], packed[i])].sum(axis=1)
        hist_all += np.bincount(d, minlength=65)
        keep = ~(is_flag[i] | is_flag[i + 1:])
        hist_noflag += np.bincount(d[keep], minlength=65)
        nearest[i] = min(nearest[i], d.min())
        nearest[i + 1:] = np.minimum(nearest[i + 1:], d)
    pairs_all, pairs_nf = int(hist_all.sum()), int(hist_noflag.sum())

    # positives
    sample = rng.sample(range(n), min(n_pos, n))
    dist = {}
    for idx in sample:
        img = load(pkg, base[idx][0])
        other = load(pkg, base[rng.randrange(n)][0])
        h0 = phash_hex(img)
        for name, t in transforms(img, other, rng).items():
            dist.setdefault(name, []).append(bin(int(h0, 16) ^ int(phash_hex(t), 16)).count("1"))

    L = ["<!-- generated by scripts/narrative/image_robustness.py -->",
         f"Corpus: emoji-datasource-twitter {version} (Twemoji 64x64 PNG, upscaled to 256x256, alpha flattened on "
         f"white). {n} distinct base images (skin-tone variants and Component category excluded); "
         f"{int(is_flag.sum())} of them are flags. Positive sample: {len(sample)} images, seed {SEED}.", "",
         "### Positives: Hamming distance between an image and its edited copy", "",
         "| edit | median | p90 | max | " + " | ".join(f"<= {t}" for t in THRESHOLDS) + " |",
         "|---|---|---|---|" + "---|" * len(THRESHOLDS)]
    for name, ds in dist.items():
        a = np.array(ds)
        L.append(f"| {name} | {int(np.median(a))} | {int(np.percentile(a, 90))} | {a.max()} | " +
                 " | ".join(f"{(a <= t).mean():.1%}" for t in THRESHOLDS) + " |")
    L += ["", "### Negatives: distinct images whose hashes fall within the threshold", "",
          "| threshold | pairs within, all | rate per pair, all | pairs within, flags excluded | rate per pair, "
          "flags excluded | images with any other image within |",
          "|---|---|---|---|---|---|"]
    for t in THRESHOLDS:
        a, b = int(hist_all[: t + 1].sum()), int(hist_noflag[: t + 1].sum())
        L.append(f"| <= {t} | {a:,} of {pairs_all:,} | {a / pairs_all:.2e} | {b:,} of {pairs_nf:,} | "
                 f"{b / pairs_nf:.2e} | {(nearest <= t).mean():.1%} |")
    L += ["", f"First hashes (for reproducibility): {', '.join(f'{base[i][0]}={hexes[i]}' for i in range(len(hexes)))}"]
    open(out, "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
