from beginner_ux import CouponReadiness, readiness_guidance


def readiness(status="VÄNTA", blockers=(), score=40):
    return CouponReadiness(score, status, "x", tuple(blockers), 6, 13)


def test_demo_tells_user_to_fetch_real_coupon():
    g = readiness_guidance(readiness("DEMO – INTE SPELKLAR"), demo=True)
    assert g.headline == "HÄMTA RIKTIG KUPONG"
    assert "aktuella Stryktipskupongen" in g.next_step
    assert g.tone == "error"


def test_missing_market_is_hard_stop_with_action():
    g = readiness_guidance(readiness(blockers=("aktuella marknadsodds saknas för 2 av 13 matcher",)), market_missing_count=2)
    assert g.headline == "SPELA INTE ÄNNU"
    assert "2 av 13" in g.message
    assert "Analysera kupongen igen" in g.next_step


def test_missing_lineups_advises_reanalysis_near_deadline():
    g = readiness_guidance(readiness("NÄSTAN SPELKLAR", blockers=("bekräftade startelvor saknas för 8 av 13 matcher",), score=65))
    assert g.headline == "VÄNTA OM DU KAN"
    assert "närmare spelstopp" in g.next_step


def test_source_conflict_is_explicit():
    g = readiness_guidance(readiness("NÄSTAN SPELKLAR", blockers=("2 källkonflikt(er) behöver granskas",), score=61))
    assert g.headline == "KONTROLLERA UNDERLAGET"
    assert "Expertläge" in g.next_step


def test_ready_status_does_not_claim_certainty():
    g = readiness_guidance(readiness("SPELKlar".upper(), score=82))
    assert g.headline == "SYSTEMET KAN ANVÄNDAS"
    assert "aktuella systemförslag" in g.message
    assert "garanti" not in (g.message + g.next_step).lower()
    assert g.tone == "success"
