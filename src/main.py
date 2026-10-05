import sys  # we need sys for command line arguments (sys.argv) and for stdout / stderr

# =====================================================================================================
# WHOLE PROGRAM IN SHORT (use this if exam asks "explain your program")
# How does your program work?
# A: We read both files as lines (bytes). diff_marks() runs Myers O(ND) diff on them and gives two arrays:
#    del_a (1 = line of A deleted) and ins_b (1 = line of B inserted). Matched lines stay 0.
#    Myers is done in linear space: instead of saving the V array of every d, we search from the start (forward)
#    and from the end (backward) at the same time. When they meet we get the middle snake. The snake is matched,
#    and the left part and right part are solved the same way (divide and conquer, with a stack).
#    build_output() walks both files with the marks and prints " " (same), "-" (deleted), "+" (inserted).
#    In highlight mode, for every "-" / "+" pair we run the same diff again on the characters, and ranges()
#    converts the 0/1 marks into text like "1-2". Time is O(N*D), memory is O(N).
# =====================================================================================================

USAGE = "usage: main.py lines|highlight A_PATH B_PATH"  # reason: one place for the message, so we print the same text every time arguments are wrong


def read_lines(path):  # we read one file and return list of lines, every line is bytes
    """# -----------------------------------------------------------------------------------------------------
    #Why do you read the file as bytes (rb) and why do you pop the last element?
    # A: Binary mode means any file opens without a decoding error, and two lines are same only if their bytes are exactly
    #    same. split(b"\n") gives one extra empty element when the file ends with a newline ("a\nb\n" -> a, b, empty),
    #    but that is not a real third line, so we pop it. A file without trailing newline has no empty element, so no pop.
    # -----------------------------------------------------------------------------------------------------"""
    with open(path, "rb") as f:  # reason: binary mode, so any file (even with bad utf-8) opens and no decoding error comes, and "same line" means exactly same bytes
        lines = f.read().split(b"\n")  # we read all bytes and cut at every newline, so one element = one line
    if lines and not lines[-1]:  # if file ends with newline, split gives one extra empty element at the end
        lines.pop()  # reason: "a\nb\n" is 2 lines not 3, a trailing newline is not a new logical line
    return lines  # list of byte lines


def middle_snake(A, B, Ar, Br, n, m):  # we find the middle snake of the edit graph, A/B normal, Ar/Br reversed, n=len(A), m=len(B)
    """# -----------------------------------------------------------------------------------------------------
    # What is the edit graph, what is diagonal k, and what does the V array store?
    # A: Edit graph is a grid, x goes along A (0..n) and y goes along B (0..m). Moving right (x+1) = delete A[x],
    #    moving down (y+1) = insert B[y], moving diagonal (x+1,y+1) = free, allowed only if A[x] == B[y] (this is a snake).
    #    Diagonal k = x - y. Goal is to go from (0,0) to (n,m) with the fewest right/down moves (D = edit distance).
    #    V array: V[k] = the furthest x we reached on diagonal k using d edits. y is not stored because y = x - k.
    #
    #Why middle snake? Why not normal Myers with a trace?
    # A: Normal Myers saves a copy of V for every d to walk back, so memory is O(D^2). Here we run a forward search
    #    from (0,0) and a backward search from (n,m) (on reversed strings) at the same time, each only up to D/2.
    #    When they meet we get one snake that is on an optimal path. We solve left of it and right of it again,
    #    so we never need the trace. Memory becomes O(N) and time stays O(ND).
    #
    # TRACE for teacher example  A = a b c a b b a (n=7),  B = c b a b a c (m=6),  delta = n - m = 1 (odd)
    #   Forward V (k: x)                      Backward V on reversed strings (k: x)
    #   d=0 : 0:0                             d=0 : 0:0
    #   d=1 : -1:0  1:1                       d=1 : -1:2  1:1
    #   d=2 : -2:2  0:2  2:3                  d=2 : -2:3  0:4  2:2
    #   d=3 : -3:3 -1:4  1:5   <- forward d=3, k=1 reaches x=5,y=4. Backward diagonal = delta - k = 0, vb[0] = 4.
    #                             x + xb = 5 + 4 = 9 >= n = 7 -> they met -> return snake (3,2) -> (5,4)
    #   So middle snake = (3,2)->(5,4): it is the matched pair "a b" (A[3..4] = a b equals B[2..3] = a b), 2 free diagonal steps.
    #   The full result is: deleted a, c, second b of A; inserted first c and last c of B  (D = 5).
    #   (d=3 forward + d=2 backward = 5 edits, that is why odd delta meets at forward d, backward d-1)
    # -----------------------------------------------------------------------------------------------------"""
    # Edit graph: x goes along A, y goes along B. Right move = delete from A, down move = insert from B,
    # diagonal move (snake) = free, only when A[x] == B[y]. Diagonal number k = x - y.
    delta = n - m  # difference of lengths, this is the diagonal where the end point (n, m) lies
    odd = delta & 1  # 1 if delta is odd, 0 if even. Reason: this decides in which search (forward or backward) the two paths can meet first
    max_d = (n + m + 1) // 2  # reason: total edits D is at most n+m, and each search goes only half of it, so we need only ceil((n+m)/2) rounds
    off = max_d + 1  # reason: k can be negative and python list index cannot, so we use index = off + k to shift everything to positive
    vf = [-1] * (2 * max_d + 3)  # V array for forward search: vf[k] = furthest x reached on diagonal k (-1 = not reached). Size covers k from -max_d-1 to max_d+1
    vb = vf[:]  # V array for backward search, same idea but on the reversed sequences (copy, so both are separate lists)
    vf[off + 1] = vb[off + 1] = 0  # reason (trick): at d=0, k=0 takes x = V[k+1] = 0, so the search starts from x=0 without a special case
    fs = fe = bs = be = 0  # how many diagonals we trimmed from start/end (forward and backward). Reason: diagonals that left the graph are useless, we skip them

    for d in range(max_d + 1):  # d = number of edits (non diagonal moves) used so far, we grow it one by one so the first meeting is the shortest path
        # ---------- forward search ----------
        # Why range(-d + fs, d - fe + 1, 2) with step 2?
        # A: After exactly d edits, k = (number of rights) - (number of downs), and rights + downs = d, so k has the
        #    same parity as d. That is why only -d, -d+2, ..., d are possible and we step by 2.
        for k in range(-d + fs, d - fe + 1, 2):  # reason: after d edits k always has same parity as d, so only -d, -d+2, ... d are possible, that is why step is 2
            i = off + k  # index of diagonal k inside the list
            # Explain the condition  k == -d or (k != d and vf[i-1] < vf[i+1])
            # A: To reach diagonal k at step d we come from k-1 (right move, x+1) or from k+1 (down move, x same).
            #    At k = -d there is no k-1 reached yet, so we must come from k+1. At k = d there is no k+1, so we must
            #    come from k-1. In the middle both exist and we choose the one that reached further x (greedy:
            #    furthest reaching path is always at least as good).
            if k == -d or (k != d and vf[i - 1] < vf[i + 1]):  # reason: at the edge k=-d only k+1 exists, at k=d only k-1 exists, in the middle we pick the neighbour that reached further (greedy)
                x = vf[i + 1]  # come from diagonal k+1 by a down move (insert), x stays same
            else:  # otherwise come from diagonal k-1
                x = vf[i - 1] + 1  # right move (delete), x increases by 1
            y = x - k  # from k = x - y we get y
            x0, y0 = x, y  # we remember where the snake starts, because we may need to return it as the middle snake
            #Why the while loop and why x < n and y < m is checked first?
            # A: The while loop follows the snake: as long as A[x] == B[y] we move diagonally for free (no edit cost),
            #    so we always go as far as possible on this diagonal. The bounds check comes first so we never read
            #    A[n] or B[m] (outside the list).
            while x < n and y < m and A[x] == B[y]:  # follow the snake: while both elements are equal move diagonally for free (no edit cost). Bounds check first so we never read outside
                x += 1  # one step in A
                y += 1  # one step in B
            vf[i] = x  # save the furthest x we reached on this diagonal for this d (this is the V array value we trace by hand in exam)
            # Why do you trim with fe += 2 / fs += 2 and then continue?
            # A: x > n means this diagonal went out of the graph on the right, y > m means it went out at the bottom.
            #    A point outside the graph is not valid, so we must not use it for overlap check (continue). Also
            #    the next d would also go outside on this side, so we shrink the range of k (fe or fs grows by 2
            #    because k moves by 2) and skip these diagonals later. It saves time and avoids wrong results.
            if x > n:  # this diagonal went outside the graph on the right side (came by a right move from x = n)
                fe += 2  # reason: all further diagonals on this side are also outside, so we trim the upper end, next d will not use it
                continue  # and we do not check overlap for it, a point outside the graph is not valid
            if y > m:  # this diagonal went outside the graph at the bottom
                fs += 2  # so we trim the lower end
                continue  # skip overlap check
            # Why do you check for overlap inside the innermost loop, not at the end of the d iteration?
            # A: The overlap check is done right after each diagonal is computed. The moment forward and backward
            #    paths touch (x + xb >= n) we already have the middle snake, so we return immediately. Edit distance is
            #    the smallest d where they meet, and the first meeting is on a shortest path. If we waited until the
            #    end of the d iteration we would waste work and could pick a snake from a later diagonal
            #    (not guaranteed to be on an optimal path), or the V array of this d would be changed by other k.
            #
            # Why odd delta checks in the forward search and even delta checks in the backward search?
            # A: Total edit distance D = forward d + backward d. If delta is odd, D is odd, so the paths first meet when
            #    forward has d edits and backward has d-1 (forward is one step ahead), so we check after the forward
            #    step, and backward diagonals only go up to |k| < d, that is why  -d < kb < d.
            #    If delta is even, D is even, both have the same d when they meet, so we check after the backward
            #    step with  -d <= kf <= d.
            #
            # Why kb = delta - k? And why x + xb >= n?
            # A: The backward search runs on reversed strings, so a point (x,y) in normal coordinates is (n-x, m-y) in
            #    reversed coordinates. Diagonal k' = (n-x)-(m-y) = delta - (x-y) = delta - k. So forward diagonal k is
            #    the same diagonal as backward diagonal delta - k. xb is measured from the end, so the real x of the
            #    backward path is n - xb. They met when x >= n - xb, which is x + xb >= n.
            if odd and -d < delta - k < d:  # reason: delta odd means total D is odd, so forward step d meets backward step d-1. Backward diagonal is delta - k (reversed coordinates flip k) and backward has only reached |k| < d
                xb = vb[off + delta - k]  # furthest x of backward search on the matching diagonal
                if xb != -1 and x + xb >= n:  # reason: xb is measured from the end (reversed), so x + xb >= n means forward and backward paths touched or crossed on this diagonal
                    return x0, y0, x, y  # we found the middle snake, we return it right now. Reason: the first meeting is the shortest path, waiting for end of d loop is useless and may give a longer one

        # ---------- backward search ----------
        #How is the backward search different?
        # A: It is the same code but on the reversed strings Ar, Br, so it starts at (n,m) and walks to (0,0). When it
        #    meets the forward search we convert the snake back with (n - x, m - y) because it is in reversed coordinates.
        for k in range(-d + bs, d - be + 1, 2):  # same as forward but on the reversed strings, it starts from the end point (n, m) and walks to (0, 0)
            i = off + k  # index of diagonal k (in reversed coordinates)
            if k == -d or (k != d and vb[i - 1] < vb[i + 1]):  # same rule for choosing the previous diagonal (edge cases, else furthest reaching)
                x = vb[i + 1]  # down move
            else:
                x = vb[i - 1] + 1  # right move
            y = x - k  # y from x and k
            x0, y0 = x, y  # snake start in reversed coordinates
            while x < n and y < m and Ar[x] == Br[y]:  # follow the snake on reversed sequences (matching from the end of the original)
                x += 1  # one step
                y += 1  # one step
            vb[i] = x  # save furthest reversed x
            if x > n:  # left the graph on the right
                be += 2  # trim upper end
                continue
            if y > m:  # left the graph at the bottom
                bs += 2  # trim lower end
                continue
            if not odd and -d <= delta - k <= d:  # reason: delta even means total D is even, so backward step d meets forward step d (same d), that is why <= here and < in the odd case
                xf = vf[off + delta - k]  # forward furthest x on the matching diagonal (forward k = delta - backward k)
                if xf != -1 and xf + x >= n:  # same overlap test, forward x + backward x >= n
                    return n - x, m - y, n - x0, m - y0  # reason: the snake is in reversed coordinates, so we convert back to normal: (n - x, m - y) is start, (n - x0, m - y0) is end

    raise RuntimeError("middle snake not found")  # should never happen, because for any two non empty sequences a middle snake always exists


def diff_marks(a, b):  # main diff function: returns del_a (1 = this element of a is deleted) and ins_b (1 = this element of b is inserted), 0 = matched
    """# -----------------------------------------------------------------------------------------------------
    # What does diff_marks return and how does it work step by step?
    # A: It returns del_a and ins_b (bytearrays), 1 = this element is edited, 0 = matched. Steps: (1) give every item an
    #    integer id, (2) throw out items that are only in one sequence, (3) solve the rest with a stack of sub problems:
    #    strip common prefix/suffix, handle empty side, else find middle snake and split in two, (4) map the marks back to
    #    the original positions. The same function is used for lines (Part A) and for characters (Part B).
    # -----------------------------------------------------------------------------------------------------"""
    na, nb = len(a), len(b)  # lengths of both sequences

    # Why do you convert items to integer ids?
    # A: Items can be long byte strings (lines). Comparing them again and again inside the snake loop is slow. With ids
    #    every comparison is a fast int compare. setdefault gives equal items the same id from one shared dictionary.
    ids = {}  # item -> id
    ia = [ids.setdefault(x, len(ids)) for x in a]  # ids of a, a new item gets next free number
    ib = [ids.setdefault(x, len(ids)) for x in b]  # ids of b, same dictionary so equal items always get equal ids

    # Why do you remove items that appear in only one sequence?
    # A: An item that is not in the other sequence can never be matched, so it is surely a delete (if in a) or an insert
    #    (if in b). Removing them first makes both sequences shorter and D smaller, so Myers is faster and result is same.
    #    ma / mb remember the original positions so we can put the result back later.
    in_a, in_b = set(ia), set(ib)  # which ids exist in a and in b
    ma = [i for i, v in enumerate(ia) if v in in_b]  # original positions in a that survive the filter (we need them to map result back)
    mb = [j for j, v in enumerate(ib) if v in in_a]  # original positions in b that survive the filter
    fa = [ia[i] for i in ma]  # filtered a (ids only)
    fb = [ib[j] for j in mb]  # filtered b (ids only)

    del_f = bytearray(len(fa))  # delete marks for filtered a, all 0 at start (bytearray is small and fast, supports slice assign and find)
    ins_f = bytearray(len(fb))  # insert marks for filtered b, all 0 at start
    stack = [(0, len(fa), 0, len(fb))]  # work list: each tuple is a sub problem a[a0:a1] vs b[b0:b1]. Reason: stack instead of recursion, so python recursion limit never breaks on big files

    # Why a stack and not recursion? Why is the right part pushed first?
    # A: Divide and conquer can go deep on big files and python recursion has a limit, so we use our own stack
    #    (same logic, no limit). Stack is last in first out, so we push the right part first and the left part
    #    second, then the left part is popped and solved next (order does not change the result, it only keeps it
    #    left to right).
    while stack:  # until no sub problem is left
        a0, a1, b0, b1 = stack.pop()  # take one sub problem

        #Why strip the common prefix (and suffix) before the main search, and what invariant does it give?
        # A: Equal elements at the start (or end) can always be matched for free, no edit is needed, so we just move
        #    a0/b0 forward (a1/b1 backward). It is cheap O(N) and makes the problem smaller before the costly
        #    middle_snake. Invariant after stripping: the remaining part a[a0:a1], b[b0:b1] has its first elements
        #    different and its last elements different (or one side is empty), and every element outside it is already
        #    matched. So the remaining part is an independent sub problem and all the edits are inside it.
        while a0 < a1 and b0 < b1 and fa[a0] == fb[b0]:  # common prefix: equal elements at the start are matched, no edit needed
            a0 += 1  # shrink from the left in a
            b0 += 1  # shrink from the left in b
        while a0 < a1 and b0 < b1 and fa[a1 - 1] == fb[b1 - 1]:  # common suffix: equal elements at the end are matched too
            a1 -= 1  # shrink from the right in a
            b1 -= 1  # shrink from the right in b

        #Why do you skip the main search (middle_snake) when one side is empty? What does it tell about the sequences?
        # A: If a part is empty, there is nothing to match with, so everything in the other part is an edit: all of b
        #    is inserted (a0 == a1) or all of a is deleted (b0 == b1). Edit distance is just that length, so no search
        #    is needed, and middle_snake also needs both sides non empty. If BOTH are empty (a0 == a1 and b0 == b1)
        #    the two sequences were completely equal after stripping, nothing is marked (the slice is empty),
        #    so the two inputs are identical and the diff is empty.
        if a0 == a1:  # a part is empty, so everything left in b must be inserted (nothing to match with)
            ins_f[b0:b1] = b"\x01" * (b1 - b0)  # mark all of b[b0:b1] as inserted
            continue  # this sub problem is finished
        if b0 == b1:  # b part is empty, so everything left in a must be deleted
            del_f[a0:a1] = b"\x01" * (a1 - a0)  # mark all of a[a0:a1] as deleted
            continue  # finished. Reason for both checks: middle_snake needs both sides non empty, and these cases need no search at all

        A, B = fa[a0:a1], fb[b0:b1]  # the remaining part we have to solve
        n, m = a1 - a0, b1 - b0  # its lengths
        sx, sy, ex, ey = middle_snake(A, B, A[::-1], B[::-1], n, m)  # find the middle snake, we also pass reversed copies because the backward search walks on reversed sequences

        # Why can you split the problem at the middle snake? Why a0 + ex and not just ex?
        # A: The middle snake is on an optimal path, so best path = best path to the snake start + the snake (free,
        #    matched, stays 0) + best path from the snake end. So the two sides are independent and we solve them
        #    separately. sx, sy, ex, ey are relative to this sub problem (A and B start at 0), so we add a0 / b0 to get
        #    positions in the big filtered arrays.
        stack.append((a0 + ex, a1, b0 + ey, b1))  # right part: from end of snake to the end. We add a0/b0 because sx..ey are relative to the sub problem. Pushed first so it is solved later
        stack.append((a0, a0 + sx, b0, b0 + sy))  # left part: from start to start of snake (popped next)

    #Why do del_a and ins_b start with all 1 and then you copy the filtered result?
    # A: Items that were removed by the filter (only in one sequence) are real edits, so their mark must stay 1. Only
    #    the items that survived the filter have a real status from Myers (0 matched, 1 edited), so we copy that back
    #    using the saved original positions ma / mb.
    del_a = bytearray(b"\x01") * na  # reason: everything starts as changed, because the removed (unique) items really are changed
    ins_b = bytearray(b"\x01") * nb  # same for b
    for fi, oi in enumerate(ma):  # fi = filtered index, oi = original index
        del_a[oi] = del_f[fi]  # surviving items take their real status (0 matched, 1 deleted)
    for fi, oi in enumerate(mb):
        ins_b[oi] = ins_f[fi]  # same for b (0 matched, 1 inserted)
    return del_a, ins_b  # marks for a and b


def ranges(marks):  # this turns the 0/1 marks of a character diff into text like "2-4,7-8", used by highlight
    """# -----------------------------------------------------------------------------------------------------
    #How does your highlight code turn a character diff into ranges?
    # A: For a deleted line and an inserted line we call diff_marks on their characters, so we get a 0/1 array for the old
    #    line and one for the new line (1 = changed character). ranges() scans that array: find(1) gives where a changed
    #    run starts, find(0, start) gives where it ends (end is exclusive, like a python slice), we save "start-end"
    #    and continue after end. Example: old "abc", new "axc": b and x are unique so they stay 1, a and c are matched,
    #    marks old = [0,1,0] and new = [0,1,0], so the output is "? 1-2 | 1-2". If nothing changed it prints ".".
    #    Two runs example: marks [1,1,0,0,1] -> "0-2,4-5".
    # -----------------------------------------------------------------------------------------------------"""
    n = len(marks)  # length of the mark array
    parts = []  # list of "start-end" strings
    start = marks.find(1)  # first position of a 1 = start of the first changed run
    while start != -1:  # while there is a changed run
        end = marks.find(0, start)  # first 0 after start = the run ends there. End is exclusive (like python slices), so run is [start, end)
        if end == -1:  # no 0 after it, so the run goes till the end
            end = n  # end is the length
        parts.append(f"{start}-{end}")  # save this run as start-end
        if end >= n:  # we reached the end of the array
            break  # reason: marks.find(1, n) would be pointless, nothing more to find
        start = marks.find(1, end)  # next changed run begins at the next 1 after end
    return ",".join(parts) or "."  # join runs with comma, if there is no changed run the join is empty so we print "." (means no change)


def build_output(a, b, del_a, ins_b, highlight):  # we build the final output lines from the marks
    """# -----------------------------------------------------------------------------------------------------
    # How does build_output create the final diff from the marks?
    # A: We keep two pointers i (in A) and j (in B). We look for the next 1 in del_a and in ins_b. The lines before that
    #    are unchanged, so we print them with " " and move both pointers together (matched lines are one to one). Then
    #    we take one block of edits: a[i:de] (deleted) and b[j:ie] (inserted), print all deletes with "-" first and then
    #    inserts with "+" (deletes are always before inserts). In highlight mode the k-th "+" is paired with the k-th
    #    "-" and gets a "?" marker line with the changed character ranges. At the end we print the unchanged tail.
    #
    # Why min(count, nd - i, ni - j)?
    # A: Unchanged lines must stop before the nearest edit in either file, so we take the smallest distance.
    # -----------------------------------------------------------------------------------------------------"""
    na, nb = len(a), len(b)  # lengths
    out = []  # output lines (bytes)
    i = j = 0  # i = current position in a, j = current position in b

    while True:  # we go through both files together
        nd = del_a.find(1, i)  # position of next deleted line in a
        ni = ins_b.find(1, j)  # position of next inserted line in b
        if nd == -1 and ni == -1:  # no edit left anywhere
            break  # only the unchanged tail remains

        count = na - i  # unchanged lines before next edit, start with all remaining lines of a
        if nd != -1:  # if a has an edit coming
            count = min(count, nd - i)  # unchanged run cannot go past it
        if ni != -1:  # if b has an edit coming
            count = min(count, ni - j)  # unchanged run cannot go past it either
        if count:  # if there are unchanged lines
            out.extend(b" " + line for line in a[i:i + count])  # print them with a space in front (we use a, because matched lines are same in a and b)
            i += count  # move in a
            j += count  # move in b by the same amount, reason: matched lines are one to one, so both pointers move together

        de = del_a.find(0, i)  # end of the block of deleted lines (first matched line after i)
        de = na if de == -1 else de  # if there is none, block goes to the end of a
        ie = ins_b.find(0, j)  # end of the block of inserted lines
        ie = nb if ie == -1 else ie  # if there is none, block goes to the end of b
        deleted, inserted = a[i:de], b[j:ie]  # the lines of this one edit block (can have only deletes, only inserts or both)

        out.extend(b"-" + line for line in deleted)  # first all deletes, with "-" in front (reason: deletes are always printed before inserts, same as the standard diff style)
        for index, line in enumerate(inserted):  # then the inserts one by one
            out.append(b"+" + line)  # insert line with "+" in front
            if highlight and index < len(deleted):  # reason: a changed line looks like one delete + one insert, so the k-th insert is paired with the k-th delete; extra inserts have no partner, so no marker
                old = deleted[index].decode("utf-8", "surrogateescape")  # bytes to string so we can diff character by character (not byte by byte, so one character is not split). surrogateescape keeps invalid bytes safe, no crash
                new = line.decode("utf-8", "surrogateescape")  # same for the new line
                dm, im = diff_marks(old, new)  # reason: we reuse the same Myers diff, now the items are characters instead of lines, so the 0/1 marks tell which characters changed
                out.append(f"? {ranges(dm)} | {ranges(im)}".encode("utf-8"))  # marker line: changed char ranges in old | changed char ranges in new (ranges() converts marks to text)

        i, j = de, ie  # jump past this edit block in both files

    out.extend(b" " + line for line in a[i:])  # unchanged tail after the last edit (loop broke when no edit is left)
    return out  # all output lines


def main():  # program starts here
    """# -----------------------------------------------------------------------------------------------------
    # Walk through main(). What does the program return in each case?
    # A: It checks we got exactly 3 arguments (mode, file A, file B) and the mode is lines or highlight, else prints
    #    usage and returns 2. Then it reads both files (returns 2 with an error message if a file cannot be read), runs
    #    diff_marks on the lines, builds the output and writes raw bytes to stdout. Returns 0 on success. Usage and errors
    #    go to stderr so stdout only has the diff.
    # -----------------------------------------------------------------------------------------------------"""
    if len(sys.argv) != 4 or sys.argv[1] not in ("lines", "highlight"):  # we need exactly: mode, file A, file B and mode must be valid
        print(USAGE, file=sys.stderr)  # show usage on stderr (reason: stdout is only for diff result)
        return 2  # exit code 2 = wrong usage

    try:  # reading files can fail
        a = read_lines(sys.argv[2])  # lines of file A
        b = read_lines(sys.argv[3])  # lines of file B
    except OSError as exc:  # file missing or not readable
        print(f"error: cannot read file: {exc}", file=sys.stderr)  # tell the reason on stderr
        return 2  # exit code 2

    del_a, ins_b = diff_marks(a, b)  # run Myers on the lines, we get delete marks and insert marks
    output = build_output(a, b, del_a, ins_b, sys.argv[1] == "highlight")  # highlight is True only for the highlight command

    if output:  # if there is something to print (two same files give empty output)
        sys.stdout.buffer.write(b"\n".join(output) + b"\n")  # reason: write raw bytes so no encoding changes the file content; lines joined by newline, plus last newline
        sys.stdout.buffer.flush()  # make sure everything is written
    return 0  # success


if __name__ == "__main__":  # run main only when this file is started directly
    raise SystemExit(main())  # exit with the code that main returns