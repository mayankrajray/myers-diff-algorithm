import sys


def read_file_lines(path):
    """Read file as raw bytes and split into lines according to spec."""
    try:
        with open(path, "rb") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file {path}: {e}", file=sys.stderr)
        return None
    
    # Split on newline byte
    lines = content.split(b"\n")
    
    # If last piece is empty, drop it
    if lines and lines[-1] == b"":
        lines.pop()
    
    return lines


def myers_diff(a, b):
    """
    Myers' O(ND) diff algorithm.
    Returns list of (operation, index_a, index_b, element) tuples.
    operation: 'keep', 'delete', 'insert'
    """
    n = len(a)
    m = len(b)
    max_d = n + m
    
    # V[k] = x coordinate of the end of furthest reaching path on diagonal k
    v = {1: 0}
    trace = []
    
    # Search for the shortest edit script
    for d in range(max_d + 1):
        trace.append(v.copy())
        
        for k in range(-d, d + 1, 2):
            # Decide whether to move down or right
            if k == -d or (k != d and v.get(k - 1, -1) < v.get(k + 1, -1)):
                # Move down (insert from B)
                x = v.get(k + 1, 0)
            else:
                # Move right (delete from A)
                x = v.get(k - 1, 0) + 1
            
            y = x - k
            
            # Follow diagonal (matching elements)
            while x < n and y < m and a[x] == b[y]:
                x += 1
                y += 1
            
            v[k] = x
            
            # Check if we reached the end
            if x >= n and y >= m:
                return backtrack(a, b, trace, d)
    
    return []


def backtrack(a, b, trace, d):
    """Backtrack through the trace to build the edit script."""
    n = len(a)
    m = len(b)
    x, y = n, m
    
    edits = []
    
    for depth in range(d, -1, -1):
        v = trace[depth]
        k = x - y
        
        # Determine previous k
        if k == -depth or (k != depth and v.get(k - 1, -1) < v.get(k + 1, -1)):
            prev_k = k + 1
        else:
            prev_k = k - 1
        
        prev_x = v.get(prev_k, 0)
        prev_y = prev_x - prev_k
        
        # Follow diagonal backwards
        while x > prev_x and y > prev_y:
            x -= 1
            y -= 1
            edits.append(("keep", x, y, a[x]))
        
        # Record the edit
        if depth > 0:
            if y == prev_y:
                # Deletion
                x -= 1
                edits.append(("delete", x, -1, a[x]))
            else:
                # Insertion
                y -= 1
                edits.append(("insert", -1, y, b[y]))
        
        x, y = prev_x, prev_y
    
    edits.reverse()
    return edits


def format_lines_output(edits):
    """Format the diff for lines command with delete-first ordering."""
    output = []
    i = 0
    
    while i < len(edits):
        op = edits[i][0]
        
        if op == "keep":
            # Keep line
            output.append((b" ", edits[i][3]))
            i += 1
        else:
            # Start of a change block - collect all deletes and inserts
            deletes = []
            inserts = []
            
            while i < len(edits) and edits[i][0] != "keep":
                if edits[i][0] == "delete":
                    deletes.append(edits[i][3])
                else:  # insert
                    inserts.append(edits[i][3])
                i += 1
            
            # Output deletes first, then inserts
            for line in deletes:
                output.append((b"-", line))
            for line in inserts:
                output.append((b"+", line))
    
    return output


def get_codepoints(byte_line):
    """Convert bytes to list of Unicode code points."""
    try:
        text = byte_line.decode("utf-8")
        return list(text)
    except:
        # If not valid UTF-8, treat as bytes
        return list(byte_line)


def format_ranges(ranges):
    """Format list of (start, end) tuples as range string."""
    if not ranges:
        return "."
    
    # Merge adjacent ranges
    merged = []
    for start, end in sorted(ranges):
        if merged and merged[-1][1] == start:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    
    return ",".join(f"{s}-{e}" for s, e in merged)


def char_diff_ranges(old_line, new_line):
    """
    Compute character-level diff ranges.
    Returns (old_ranges, new_ranges) as lists of (start, end) tuples.
    """
    old_chars = get_codepoints(old_line)
    new_chars = get_codepoints(new_line)
    
    edits = myers_diff(old_chars, new_chars)
    
    old_ranges = []
    new_ranges = []
    
    old_pos = 0
    new_pos = 0
    
    for op, _, _, char in edits:
        if op == "keep":
            old_pos += 1
            new_pos += 1
        elif op == "delete":
            old_ranges.append((old_pos, old_pos + 1))
            old_pos += 1
        elif op == "insert":
            new_ranges.append((new_pos, new_pos + 1))
            new_pos += 1
    
    return (old_ranges, new_ranges)


def format_highlight_output(edits):
    """Format the diff for highlight command with character ranges."""
    output = format_lines_output(edits)
    
    # Find change blocks and pair lines
    i = 0
    result = []
    
    while i < len(output):
        prefix, line = output[i]
        
        if prefix == b" ":
            result.append((prefix, line, None))
            i += 1
        else:
            # Start of change block
            deletes = []
            inserts = []
            
            while i < len(output) and output[i][0] != b" ":
                if output[i][0] == b"-":
                    deletes.append(output[i][1])
                else:  # b"+"
                    inserts.append(output[i][1])
                i += 1
            
            # Compute character ranges for paired lines
            pairs = min(len(deletes), len(inserts))
            char_ranges = []
            for j in range(pairs):
                old_ranges, new_ranges = char_diff_ranges(deletes[j], inserts[j])
                char_ranges.append((old_ranges, new_ranges))
            
            # Output ALL deletes first (delete-first rule)
            for j in range(len(deletes)):
                result.append((b"-", deletes[j], None))
            
            # Then output ALL inserts (with ranges for paired ones)
            for j in range(len(inserts)):
                if j < pairs:
                    result.append((b"+", inserts[j], char_ranges[j]))
                else:
                    result.append((b"+", inserts[j], None))
    
    return result


def main() -> int:
    if len(sys.argv) != 4 or sys.argv[1] not in ("lines", "highlight"):
        print("usage: main.py lines|highlight A_PATH B_PATH", file=sys.stderr)
        return 2
    
    command, a_path, b_path = sys.argv[1:]
    
    # Read both files as raw bytes
    a_lines = read_file_lines(a_path)
    b_lines = read_file_lines(b_path)
    
    if a_lines is None or b_lines is None:
        return 2
    
    # Compute diff using Myers' algorithm
    edits = myers_diff(a_lines, b_lines)
    
    # Format and print output
    if command == "lines":
        output = format_lines_output(edits)
        for prefix, line in output:
            sys.stdout.buffer.write(prefix + line + b"\n")
    else:  # highlight
        output = format_highlight_output(edits)
        for item in output:
            if len(item) == 3:
                prefix, line, ranges = item
                sys.stdout.buffer.write(prefix + line + b"\n")
                if ranges is not None:
                    old_ranges, new_ranges = ranges
                    range_line = f"? {format_ranges(old_ranges)} | {format_ranges(new_ranges)}\n"
                    sys.stdout.buffer.write(range_line.encode("utf-8"))
            else:
                prefix, line = item
                sys.stdout.buffer.write(prefix + line + b"\n")
    
    return 0


raise SystemExit(main())
