"""A small QR code maker (ISO/IEC 18004, byte mode, error correction M, versions 1-6), drawn as SVG.

Used to open ALFRED on a phone by scanning instead of typing an address. Made here so no QR library or online service
is needed; the test reads codes back with OpenCV's decoder.
"""
from __future__ import annotations

# version: (EC codewords per block, data codewords per block for each block), error correction level M.
BLOCKS = {1: (10, (16,)), 2: (16, (28,)), 3: (26, (44,)), 4: (18, (32, 32)), 5: (24, (43, 43)), 6: (16, (27, 27, 27, 27))}
ALIGN = {1: (), 2: (6, 18), 3: (6, 22), 4: (6, 26), 5: (6, 30), 6: (6, 34)}

EXP, LOG = [0] * 512, [0] * 256
_x = 1
for _i in range(255):
    EXP[_i], LOG[_x] = _x, _i
    _x = (_x << 1) ^ (0x11D if _x & 0x80 else 0)
for _i in range(255, 512):
    EXP[_i] = EXP[_i - 255]


def _mul(a, b):
    return 0 if a == 0 or b == 0 else EXP[LOG[a] + LOG[b]]


def _ec(data, n):
    generator = [1]
    for i in range(n):  # (x - a^0)(x - a^1)...(x - a^(n-1))
        generator = [a ^ _mul(b, EXP[i]) for a, b in zip(generator + [0], [0] + generator)]
    remainder = list(data) + [0] * n
    for i in range(len(data)):
        factor = remainder[i]
        if factor:
            for j, g in enumerate(generator):
                remainder[i + j] ^= _mul(g, factor)
    return remainder[len(data):]


def _codewords(payload: bytes):
    for version, (ec, blocks) in BLOCKS.items():
        if len(payload) + 2 <= sum(blocks):  # mode and length take 12 bits; the terminator fits in the rest
            break
    else:
        raise ValueError("Too long for a small QR code.")
    capacity = sum(blocks)
    bits = "0100" + format(len(payload), "08b") + "".join(format(b, "08b") for b in payload)
    bits += "0" * min(4, capacity * 8 - len(bits))
    bits += "0" * (-len(bits) % 8)
    data = [int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)]
    data += [(0xEC, 0x11)[i % 2] for i in range(capacity - len(data))]
    chunks, at = [], 0
    for size in blocks:
        chunks.append(data[at:at + size])
        at += size
    ecs = [_ec(chunk, ec) for chunk in chunks]
    out = [chunk[i] for i in range(max(blocks)) for chunk in chunks if i < len(chunk)]
    return version, out + [e[i] for i in range(ec) for e in ecs]


def _format_bits(mask):
    data = (0 << 3) | mask  # level M is 00
    rem = data
    for _ in range(10):
        rem = (rem << 1) ^ ((rem >> 9) * 0x537)
    return ((data << 10) | rem) ^ 0x5412


MASKS = (lambda r, c: (r + c) % 2 == 0, lambda r, c: r % 2 == 0, lambda r, c: c % 3 == 0, lambda r, c: (r + c) % 3 == 0,
         lambda r, c: (r // 2 + c // 3) % 2 == 0, lambda r, c: r * c % 2 + r * c % 3 == 0,
         lambda r, c: (r * c % 2 + r * c % 3) % 2 == 0, lambda r, c: ((r + c) % 2 + r * c % 3) % 2 == 0)


def _penalty(m):
    size, score = len(m), 0
    lines = m + [list(col) for col in zip(*m)]
    for line in lines:
        run = 1
        for a, b in zip(line, line[1:]):
            run = run + 1 if a == b else 1
            score += 3 if run == 5 else 1 if run > 5 else 0
        text = "".join("1" if v else "0" for v in line)
        score += 40 * (text.count("10111010000") + text.count("00001011101"))
    score += 3 * sum(m[r][c] == m[r][c + 1] == m[r + 1][c] == m[r + 1][c + 1] for r in range(size - 1) for c in range(size - 1))
    dark = sum(map(sum, m))
    return score + 10 * (abs(dark * 20 - size * size * 10) // (size * size))


def matrix(text: str) -> list[list[bool]]:
    version, words = _codewords(text.encode("utf-8"))
    size = 17 + 4 * version
    m = [[False] * size for _ in range(size)]
    fixed = [[False] * size for _ in range(size)]

    def put(r, c, dark):
        m[r][c], fixed[r][c] = dark, True

    for i in range(size):
        put(6, i, i % 2 == 0)
        put(i, 6, i % 2 == 0)
    for cr, cc in ((3, 3), (3, size - 4), (size - 4, 3)):
        for dr in range(-4, 5):
            for dc in range(-4, 5):
                if 0 <= cr + dr < size and 0 <= cc + dc < size:
                    put(cr + dr, cc + dc, max(abs(dr), abs(dc)) not in (2, 4))
    spots = ALIGN[version]
    for ar in spots:
        for ac in spots:
            if (ar, ac) in ((spots[0], spots[0]), (spots[0], spots[-1]), (spots[-1], spots[0])):
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    put(ar + dr, ac + dc, max(abs(dr), abs(dc)) != 1)

    def draw_format(mask):
        bits = _format_bits(mask)
        bit = [(bits >> i) & 1 == 1 for i in range(15)]
        for i in range(6):
            put(i, 8, bit[i])
        put(7, 8, bit[6])
        put(8, 8, bit[7])
        put(8, 7, bit[8])
        for i in range(9, 15):
            put(8, 14 - i, bit[i])
        for i in range(8):
            put(8, size - 1 - i, bit[i])
        for i in range(8, 15):
            put(size - 15 + i, 8, bit[i])
        put(size - 8, 8, True)

    draw_format(0)  # reserves the format areas before the data goes in
    stream = [(w >> (7 - i)) & 1 == 1 for w in words for i in range(8)]
    at, right = 0, size - 1
    while right >= 1:
        if right == 6:
            right = 5
        for vert in range(size):
            for j in range(2):
                c = right - j
                r = size - 1 - vert if ((right + 1) & 2) == 0 else vert
                if not fixed[r][c] and at < len(stream):
                    m[r][c] = stream[at]
                    at += 1
        right -= 2

    best = None
    for mask, rule in enumerate(MASKS):
        candidate = [[m[r][c] ^ (not fixed[r][c] and rule(r, c)) for c in range(size)] for r in range(size)]
        saved = [row[:] for row in m]
        m[:] = candidate
        draw_format(mask)
        score = _penalty(m)
        if best is None or score < best[0]:
            best = (score, [row[:] for row in m])
        m[:] = saved
    return best[1]


def svg(text: str, *, label: str = "QR code") -> str:
    """Black on white with the four-module quiet zone, so phones read it in light and dark themes alike."""
    m = matrix(text)
    size = len(m) + 8
    cells = "".join(f"M{c + 4} {r + 4}h1v1h-1z" for r, row in enumerate(m) for c, dark in enumerate(row) if dark)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" role="img" aria-label="{label}" '
            f'shape-rendering="crispEdges"><rect width="{size}" height="{size}" fill="#fff"/><path d="{cells}" fill="#000"/></svg>')
