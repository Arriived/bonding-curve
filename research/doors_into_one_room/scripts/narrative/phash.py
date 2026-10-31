"""64-bit DCT perceptual hash (pHash), numpy only.

Algorithm (identical to imagehash.phash 4.3.2 with hash_size=8, highfreq_factor=4, on the same input image):
  1. Composite any alpha channel onto white (token images are often transparent PNGs; imagehash's plain
     convert("L") would read whatever RGB sits under transparent pixels). This step is ours.
  2. Convert to 8-bit grayscale ("L"), resize to 32x32 with Lanczos.
  3. 2-D DCT-II (scipy.fftpack convention: unnormalised, applied along axis 0 then axis 1).
  4. Round coefficients to 6 decimals (ours: makes exact ties deterministic across platforms; symmetric images
     such as flags have coefficients that are exactly 0 in real arithmetic and +-1e-10 noise in floating point).
     Keep the top-left 8x8 block, including DC. Bit = coefficient > median of the 64.
  5. Pack row-major, first bit most significant -> 16 hex chars.
Distance = Hamming distance between the two 64-bit values.

Usage: python3 phash.py <image> [<image> ...]   -> prints "<hex>  <path>" per image
"""
import sys

import numpy as np
from PIL import Image

N = 32
_k = np.arange(N).reshape(-1, 1)
_n = np.arange(N).reshape(1, -1)
DCT = 2.0 * np.cos(np.pi * _k * (2 * _n + 1) / (2 * N))  # scipy.fftpack.dct type II, norm=None


def flatten_alpha(img):
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img)
    return img.convert("RGB")


def phash_bits(img):
    g = flatten_alpha(img).convert("L").resize((N, N), Image.Resampling.LANCZOS)
    x = np.asarray(g, dtype=np.float64)
    d = np.round(DCT @ x @ DCT.T, 6)
    low = d[:8, :8]
    return low > np.median(low)


def phash_hex(img):
    v = 0
    for b in phash_bits(img).flatten():
        v = (v << 1) | int(b)
    return f"{v:016x}"


def hamming_hex(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count("1")


if __name__ == "__main__":
    for path in sys.argv[1:]:
        with Image.open(path) as im:
            print(f"{phash_hex(im)}  {path}")
