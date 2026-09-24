from app.ingest.well_ids import canonical, slug


def test_volve_variants():
    for v in ["15/9-F-5", "NO 15/9-F-5", "15_9-F-5", "15$47$9-F-5", "no 15/9-f-5", "15/9 - F-5"]:
        assert canonical(v) == "15/9-F-5", v


def test_sodir_suffixes():
    assert canonical("1/3-10 A") == "1/3-10 A"
    assert canonical("6507/6-4 S") == "6507/6-4 S"


def test_forge():
    for v in ["16A(78)-32", "16A (78)-32", "FORGE 16A (78)-32", "Utah FORGE 16A(78)-32", "16a(78)-32", "FORGE 16A [78]-32"]:
        assert canonical(v) == "16A(78)-32", v
    for v, want in [("58-32", "58-32"), ("78B-32", "78B-32"), ("FORGE 68-32", "68-32")]:
        assert canonical(v) == want, v


def test_slug():
    assert slug("15/9-F-5") == "15-9-f-5"
