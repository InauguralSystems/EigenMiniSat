# Ordered DIMACS identity for the torus named by rows/cols, independent of the
# EigenScript emitter. Edge numbering is fixed by the checked-in 3x3 fixture:
# horizontal row-major edges, then vertical row-major edges; charge at (0,0).
# Pin exact ordered tokens. Swapping 3x3 vertex blocks 1 and 2 was measured
# to leave normalized VM output identical; the regime bank cannot catch it.
# The shell also compares 3x3 and 4x4 to captured fixtures (not this model).
function reject(message) {
    print message > "/dev/stderr"
    bad = 1
    exit 1
}
BEGIN {
    vertices = rows * cols
    # Forbidden assignments: even masks at the odd vertex, odd masks elsewhere.
    split("0 3 5 6 9 10 12 15", even, " ")
    split("1 2 4 7 8 11 13 14", odd, " ")
}
NF == 0 || $1 == "c" { next }
!header {
    if (NF != 4 || $1 != "p" || $2 != "cnf" || $3 != 2*vertices || $4 != 8*vertices)
        reject("expected p cnf " 2*vertices " " 8*vertices "; got " $0)
    header = 1
    next
}
{
    for (field = 1; field <= NF; field++) {
        if (tokens >= 40*vertices) reject("extra literal/clause after torus")
        vertex = int(tokens/40)
        clause = int((tokens%40)/5) + 1
        slot = tokens%5
        expected = 0
        if (slot < 4) {
            row = int(vertex/cols)
            col = vertex%cols
            if (slot == 0) edge = vertex+1
            if (slot == 1) edge = row*cols+(col+cols-1)%cols+1
            if (slot == 2) edge = vertices+vertex+1
            if (slot == 3) edge = vertices+((row+rows-1)%rows)*cols+col+1
            mask = vertex == 0 ? even[clause] : odd[clause]
            expected = int(mask/(2^slot))%2 ? -edge : edge
        }
        if ($field !~ /^-?[0-9]+$/ || $field+0 != expected)
            reject("token " tokens+1 ": expected " expected "; got " $field)
        tokens++
    }
}
END {
    if (!bad && (!header || tokens != 40*vertices))
        reject("incomplete torus: expected " 40*vertices " clause tokens; got " tokens+0)
}
