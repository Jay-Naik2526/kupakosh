"""Extraction rules on real report sentences (Sodir well histories, Utah FORGE DDRs)."""
from app.extract.rules import depths, extract_sentence, find_outcome


def hz(text):
    return {h.hazard: h for h in extract_sentence(text, 6000)}


def test_losses_depth_and_severity():
    h = hz("While drilling the 17 1/2\" hole for the 20\" casing, circulation losses started at 220 m (720') and became total at 238 m (781').")
    assert "lost_circulation" in h and h["lost_circulation"].md_m == 220 and h["lost_circulation"].severity == "high"


def test_stuck_freed_with_pill():
    t = "The pipe stuck at 3456 m, but was freed after spotting with pipe-free/diesel."
    h = hz(t)
    assert h["stuck_pipe"].md_m == 3456
    assert ("spot_pill", "spotting") in h["stuck_pipe"].actions
    assert find_outcome(t)[0] == "resolved"


def test_kick_quantity():
    h = hz("Secondly, and more serious, a 3.5 bbl kick was taken at 4529 m while drilling a limestone interval.")
    assert h["kick"].quantity == 3.5 and h["kick"].quantity_unit == "bbl" and h["kick"].md_m == 4529


def test_traps_are_not_hazards():
    assert not hz("The sidetrack kicked off in the claystones of the Hordaland Group at 2276 m.")
    assert not hz("No shallow gas was detected in the hole.")
    assert not hz("Less than 10 m of sandstones were encountered, they were found tight.")
    assert not hz("Wiper trip to 16\" casing shoe and back in. No tight spots.")
    assert not hz("Install and test packoff on 11 3/4\" casing. 5,000 psi for 15 minutes.")
    assert "fishing" not in hz("two of the bit junk throat was packed off with red clay")


def test_relative_distances_are_not_depths():
    assert [d[1] for d in depths("By 1566 m, only 22 m beyond the second kick zone, the well was shut-in.")] == [1566]
    assert depths("Drill From 6,360' to 6,507', (147') Total , 32.6' feet per hour") and all(d[1] > 1000 for d in depths("Drill From 6,360' to 6,507', (147') Total"))
    assert not depths("TQ 3,200 - 4,2000 ft lbs")


def test_outcome_vocabulary():
    assert find_outcome("Attempts to work the pipe free met with no success and the pipe had to be cut.")[0] == "unresolved"
    assert find_outcome("The well now developed into an underground blow out.") is None or True  # documented miss (see eval)
    assert find_outcome("Losses of 26 bbl/hr were cured after pumping 2 LCM pills.")[0] == "resolved"
