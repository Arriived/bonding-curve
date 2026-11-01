"""Check that phash.py reproduces imagehash.phash on the same (alpha-flattened) images.

Bits are compared wherever the reference coefficient differs from the median by more than 1e-6. Where it does not
(exact ties, which occur in symmetric images), imagehash's bit is floating-point noise and phash.py resolves the tie
to 0; those bits are counted separately.

Requires `pip install imagehash==4.3.2`. Usage: python3 phash_reference_check.py <package_dir> <out.txt>
"""
import json
import os
import sys

import imagehash
import numpy as np
import scipy.fftpack
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from phash import flatten_alpha, phash_bits  # noqa: E402


def main():
    pkg, out = sys.argv[1], sys.argv[2]
    if pkg == "--real":
        from fetch_token_images import CACHE, OUT
        rows = [json.loads(line) for line in (OUT / "token_images.jsonl").read_text(encoding="utf-8").splitlines()]
        unique = {row['image_sha256']: row for row in rows if row.get('phash')}
        files = [str(CACHE / unique[key]['cache_key']) for key in sorted(unique)[:500]]
    else:
        meta = json.load(open(os.path.join(pkg, "emoji.json")))
        files = [os.path.join(pkg, "img", "twitter", "64", name) for name in
                 sorted(e["image"] for e in meta if e.get("has_img_twitter"))[:500]]
    same, tie_imgs, tie_bits, bad = 0, 0, 0, 0
    for f in files:
        with Image.open(f) as im:
            img = flatten_alpha(im)
            ours = phash_bits(img).flatten()
            ref = imagehash.phash(img, hash_size=8, highfreq_factor=4).hash.flatten()
            g = np.asarray(img.convert("L").resize((32, 32), Image.Resampling.LANCZOS))
            low = scipy.fftpack.dct(scipy.fftpack.dct(g, axis=0), axis=1)[:8, :8].flatten()
            tie = np.abs(low - np.median(low)) <= 1e-6
            same += int((ours == ref).all())
            bad += int((ours[~tie] != ref[~tie]).any())
            tie_imgs += int(tie.any())
            tie_bits += int(tie.sum())
    msg = (f"imagehash {imagehash.__version__}, {len(files)} images: {same} identical 64-bit hashes; "
           f"{bad} images differ on a non-tie bit; {tie_imgs} images have exact median ties "
           f"({tie_bits} tie bits in total), where imagehash's bit is floating-point noise")
    open(out, "w", encoding="utf-8", newline="\n").write(msg + "\n")
    print(msg)
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
