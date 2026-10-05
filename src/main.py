"""Myers' O(ND) diff: line diff (Part A) and changed-character ranges (Part B)."""

import sys

USAGE = "usage: main.py lines|highlight A_PATH B_PATH"


def read_lines(path):
    with open(path, "rb") as f:
        lines = f.read().split(b"\n")
    if lines and not lines[-1]:  # trailing newline is not an extra line
        lines.pop()
    return lines


def middle_snake(A, B, Ar, Br, n, m):
    """Return the middle snake (sx, sy, ex, ey) of the Myers edit graph."""
    delta = n - m
    odd = delta & 1
    max_d = (n + m + 1) // 2
    off = max_d + 1
    vf = [-1] * (2 * max_d + 3)  # furthest x per diagonal (forward)
    vb = vf[:]                   # furthest x per diagonal (backward)
    vf[off + 1] = vb[off + 1] = 0
    fs = fe = bs = be = 0        # active diagonal boundaries

    for d in range(max_d + 1):
        # Forward search
        for k in range(-d + fs, d - fe + 1, 2):
            i = off + k
            if k == -d or (k != d and vf[i - 1] < vf[i + 1]):
                x = vf[i + 1]
            else:
                x = vf[i - 1] + 1
            y = x - k
            x0, y0 = x, y
            while x < n and y < m and A[x] == B[y]:
                x += 1
                y += 1
            vf[i] = x
            if x > n:
                fe += 2
                continue
            if y > m:
                fs += 2
                continue
            if odd and -d < delta - k < d:
                xb = vb[off + delta - k]
                if xb != -1 and x + xb >= n:
                    return x0, y0, x, y

        # Backward search
        for k in range(-d + bs, d - be + 1, 2):
            i = off + k
            if k == -d or (k != d and vb[i - 1] < vb[i + 1]):
                x = vb[i + 1]
            else:
                x = vb[i - 1] + 1
            y = x - k
            x0, y0 = x, y
            while x < n and y < m and Ar[x] == Br[y]:
                x += 1
                y += 1
            vb[i] = x
            if x > n:
                be += 2
                continue
            if y > m:
                bs += 2
                continue
            if not odd and -d <= delta - k <= d:
                xf = vf[off + delta - k]
                if xf != -1 and xf + x >= n:
                    return n - x, m - y, n - x0, m - y0

    raise RuntimeError("middle snake not found")


def diff_marks(a, b):
    """Minimal Myers diff. Returns (del_a, ins_b) bytearrays; 1 = edited, 0 = matched."""
    na, nb = len(a), len(b)

    # Compact integer ID per distinct item.
    ids = {}
    ia = [ids.setdefault(x, len(ids)) for x in a]
    ib = [ids.setdefault(x, len(ids)) for x in b]

    # Items present in only one sequence can never match.
    in_a, in_b = set(ia), set(ib)
    ma = [i for i, v in enumerate(ia) if v in in_b]
    mb = [j for j, v in enumerate(ib) if v in in_a]
    fa = [ia[i] for i in ma]
    fb = [ib[j] for j in mb]

    del_f = bytearray(len(fa))
    ins_f = bytearray(len(fb))
    stack = [(0, len(fa), 0, len(fb))]  # (a0, a1, b0, b1)

    while stack:
        a0, a1, b0, b1 = stack.pop()

        while a0 < a1 and b0 < b1 and fa[a0] == fb[b0]:  # common prefix
            a0 += 1
            b0 += 1
        while a0 < a1 and b0 < b1 and fa[a1 - 1] == fb[b1 - 1]:  # common suffix
            a1 -= 1
            b1 -= 1

        if a0 == a1:  # only insertions left
            ins_f[b0:b1] = b"\x01" * (b1 - b0)
            continue
        if b0 == b1:  # only deletions left
            del_f[a0:a1] = b"\x01" * (a1 - a0)
            continue

        A, B = fa[a0:a1], fb[b0:b1]
        n, m = a1 - a0, b1 - b0
        sx, sy, ex, ey = middle_snake(A, B, A[::-1], B[::-1], n, m)

        # Push right half first so the left half is processed next.
        stack.append((a0 + ex, a1, b0 + ey, b1))
        stack.append((a0, a0 + sx, b0, b0 + sy))

    # Everything starts as changed; surviving items get their real status.
    del_a = bytearray(b"\x01") * na
    ins_b = bytearray(b"\x01") * nb
    for fi, oi in enumerate(ma):
        del_a[oi] = del_f[fi]
    for fi, oi in enumerate(mb):
        ins_b[oi] = ins_f[fi]
    return del_a, ins_b


def ranges(marks):
    """Convert a 0/1 bytearray into 'start-end,...' ranges ('.' if none)."""
    n = len(marks)
    parts = []
    start = marks.find(1)
    while start != -1:
        end = marks.find(0, start)
        if end == -1:
            end = n
        parts.append(f"{start}-{end}")
        if end >= n:
            break
        start = marks.find(1, end)
    return ",".join(parts) or "."


def build_output(a, b, del_a, ins_b, highlight):
    """Build diff output lines; deletes are emitted before inserts."""
    na, nb = len(a), len(b)
    out = []
    i = j = 0

    while True:
        nd = del_a.find(1, i)
        ni = ins_b.find(1, j)
        if nd == -1 and ni == -1:
            break

        # Unchanged lines before the next edit.
        count = na - i
        if nd != -1:
            count = min(count, nd - i)
        if ni != -1:
            count = min(count, ni - j)
        if count:
            out.extend(b" " + line for line in a[i:i + count])
            i += count
            j += count

        # One contiguous edit block.
        de = del_a.find(0, i)
        de = na if de == -1 else de
        ie = ins_b.find(0, j)
        ie = nb if ie == -1 else ie
        deleted, inserted = a[i:de], b[j:ie]

        out.extend(b"-" + line for line in deleted)
        for index, line in enumerate(inserted):
            out.append(b"+" + line)
            if highlight and index < len(deleted):
                old = deleted[index].decode("utf-8", "surrogateescape")
                new = line.decode("utf-8", "surrogateescape")
                dm, im = diff_marks(old, new)
                out.append(f"? {ranges(dm)} | {ranges(im)}".encode("utf-8"))

        i, j = de, ie

    out.extend(b" " + line for line in a[i:])  # unchanged tail
    return out


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in ("lines", "highlight"):
        print(USAGE, file=sys.stderr)
        return 2

    try:
        a = read_lines(sys.argv[2])
        b = read_lines(sys.argv[3])
    except OSError as exc:
        print(f"error: cannot read file: {exc}", file=sys.stderr)
        return 2

    del_a, ins_b = diff_marks(a, b)
    output = build_output(a, b, del_a, ins_b, sys.argv[1] == "highlight")

    if output:
        sys.stdout.buffer.write(b"\n".join(output) + b"\n")
        sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())