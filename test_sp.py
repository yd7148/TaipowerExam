"""Offline validation of SP topology back-inference."""
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resistor_sp import find_sp_topology, build_netlist


def simulate(net):
    import re
    import os
    os.add_dll_directory(r'C:\ngspice\Spice64_dll\dll-vs')
    os.add_dll_directory(r'C:\ngspice\Spice64\bin')
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    import PySpice
    from PySpice.Spice.Netlist import Circuit
    from PySpice.Spice.Simulation import CircuitSimulator
    circ = Circuit("v")
    for line in net.splitlines():
        line = line.strip()
        if not line or line.startswith('*') or line.startswith('.') or line == '.end':
            continue
        parts = line.split()
        if parts[0].startswith('V'):
            n1, n2, val = parts[1], parts[2], parts[-1]
            circ.V(parts[0], n1, circ.gnd if n2 == '0' else n2, float(val))
        else:
            n1, n2, val = parts[1], parts[2], parts[-1]
            circ.R(parts[0], n1, circ.gnd if n2 == '0' else n2, float(val))
    return circ.simulator().operating_point(), None


def check(name, resistors, target, expected_found):
    hit = find_sp_topology(resistors, target)
    got = hit is not None
    status = "OK" if got == expected_found else "FAIL"
    print(f"{status} {name}: target {target} -> {'FOUND ' + str(float(hit[0])) if hit else 'None'}")
    if hit:
        net = build_netlist(hit[1], 10)
        a, err = simulate(net)
        try:
            key = next(k for k in a.branches if str(k).endswith('v1'))
            i = a.branches[key][0]
            print(f"      simulated I={float(i):.4f}A -> R_eq={10.0/abs(float(i)):.4f} (expect {float(hit[0]):.4f})")
        except Exception as e:
            print(f"      sim read FAILED: {e!r}")
    return got == expected_found


if __name__ == '__main__':
    ok = True
    ok &= check("sanity series {10,10}->20", [10, 10], 20, True)
    ok &= check("sanity parallel {10,10}->5", [10, 10], 5, True)
    ok &= check("sanity {10,10}->4 impossible", [10, 10], 4, False)
    print()
    ok &= check("Q1 {10,10,5,5}->4 unlikely", [10, 10, 5, 5], 4, False)
    print()
    ok &= check("Q17 {20,10,20,15,15,30}->10", [20, 10, 20, 15, 15, 30], 10, True)
    print()
    ok &= check("3R {10,20,5}->30/7=4.2857", [10, 20, 5], 30.0 / 7, True)
    print()
    print("ALL", "PASS" if ok else "FAIL")