import math

from app.engines.ledger import wilson_lb
from app.ingest.survey import min_curvature


def test_wilson_matches_formula():
    k, n, z = 7, 10, 1.96
    p = k / n
    ref = (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)
    assert abs(wilson_lb(k, n, z) - ref) < 1e-12
    assert wilson_lb(0, 0, z) == 0
    assert wilson_lb(3, 3, z) < 1  # 3/3 is not certainty


def test_min_curvature_vertical_and_build():
    out = min_curvature([(0, 0, 0), (100, 0, 0), (200, 0, 0)])
    assert abs(out[-1][0] - 200) < 1e-9
    out = min_curvature([(0, 0, 0), (100, 90, 90)])  # quarter circle radius 63.66
    r = 100 / (math.pi / 2)
    assert abs(out[-1][0] - r) < 1e-6 and abs(out[-1][2] - r) < 1e-6


def test_min_curvature_matches_forge_vendor_tvd():
    from app.ingest.forge import read_survey
    sv = read_survey("16B(78)-32")
    if sv.empty:
        return
    calc = min_curvature(list(zip(sv.md, sv.inc, sv.azi)))
    worst = max(abs(c[0] - t) for c, t in zip(calc, sv.tvd))
    assert worst < 1.0, f"TVD differs from vendor by {worst:.2f} ft"
