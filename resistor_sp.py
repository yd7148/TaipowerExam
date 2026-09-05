"""Topology back-inference: enumerate all series-parallel (SP) resistor networks
made from a given multiset of resistor values, and find one whose equivalent
resistance matches an official target R_eq.

Trees are plain nested tuples:
    ('leaf', value_fraction)
    ('series' | 'parallel', left_tree, right_tree)
Values are exact Fractions so equality is lossless.
"""
from functools import lru_cache
from fractions import Fraction


@lru_cache(maxsize=None)
def _sp_tree(vals):
    """vals: sorted tuple of Fractions. Returns {R_eq: tree_tuple}."""
    if len(vals) == 1:
        return {vals[0]: ('leaf', vals[0])}
    out = {}
    n = len(vals)
    seen = set()
    for mask in range(1, (1 << n) - 1):
        g1 = tuple(sorted(vals[i] for i in range(n) if (mask >> i) & 1))
        g2 = tuple(sorted(vals[i] for i in range(n) if not (mask >> i) & 1))
        if g1 > g2:
            continue  # consider each unordered pair of groups once
        if (g1, g2) in seen:
            continue
        seen.add((g1, g2))
        left = _sp_tree(g1)
        right = _sp_tree(g2)
        for rl, lt in left.items():
            for rr, rt in right.items():
                out.setdefault(rl + rr, ('series', lt, rt))
                out.setdefault((rl * rr) / (rl + rr), ('parallel', lt, rt))
    return out


def find_sp_topology(resistor_values, target_ohm):
    """Return (r_eq, tree) realizing a SP network whose equivalent resistance
    equals target_ohm, or None. tree is a nested ('leaf'|'series'|'parallel', ...)
    tuple that can be fed to build_netlist().
    """
    tgt = Fraction(str(target_ohm))
    vals = tuple(sorted(Fraction(str(v)) for v in resistor_values))
    net = _sp_tree(vals)
    if tgt in net:
        return tgt, net[tgt]
    for r in net:
        if r and abs(float(r) / float(tgt) - 1.0) < 1e-6:
            return r, net[r]
    return None


def build_netlist(tree, source_voltage):
    """Build a SPICE netlist: V1 (node 1 -> ground) feeding the 2-terminal
    SP network described by tree. Returns the netlist string."""
    lines = []
    counter = [0]

    def newnode():
        counter[0] += 1
        return str(counter[0])

    def assign(node_tree, a, b):
        op = node_tree[0]
        if op == 'leaf':
            lines.append(f"R{counter[0]} {a} {b} {float(node_tree[1]):g}")
            counter[0] += 1
        elif op == 'series':
            m = newnode()
            assign(node_tree[1], a, m)
            assign(node_tree[2], m, b)
        else:  # parallel: both children span (a, b)
            assign(node_tree[1], a, b)
            assign(node_tree[2], a, b)

    assign(tree, 'top', '0')
    body = "\n".join(lines)
    return (
        "* inferred SP topology\n"
        f"V1 top 0 DC {source_voltage}\n"
        f"{body}\n"
        ".end"
    )