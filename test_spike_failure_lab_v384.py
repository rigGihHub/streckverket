from facit import FacitCoupon, FacitMatch
from model_change_registry import get_model_change
from release_info import APP_VERSION
from spike_failure_lab import spike_rows, spike_band_rows, spike_failure_summary


def _coupon(cid, p=.70, hit=True, selected='1', model_top='1', market_p=.65):
    matches=[]
    for i in range(13):
        if model_top == '1': model=(p, (1-p)*.6, (1-p)*.4)
        elif model_top == 'X': model=((1-p)*.6, p, (1-p)*.4)
        else: model=((1-p)*.6, (1-p)*.4, p)
        if selected == '1': market=(market_p,(1-market_p)*.6,(1-market_p)*.4)
        elif selected == 'X': market=((1-market_p)*.6,market_p,(1-market_p)*.4)
        else: market=((1-market_p)*.6,(1-market_p)*.4,market_p)
        result=selected if hit else ('X' if selected != 'X' else '1')
        matches.append(FacitMatch(i+1,f'H{i}',f'A{i}',model,market,(.55,.25,.20),(selected,),result=result))
    return FacitCoupon(cid,'2026-09-11T10:00:00Z','Live','MAX 13',128,1,.0,tuple(matches))


def test_release_registered_non_predictive():
    assert tuple(map(int, APP_VERSION.split('.'))) >= (3,84,0)
    change=get_model_change('3.84.0')
    assert change and change.predictive_change is False


def test_spike_rows_use_probability_of_selected_sign_not_generic_top_pick():
    c=_coupon('c',p=.70,hit=False,selected='1',model_top='X',market_p=.60)
    row=spike_rows([c])[0]
    assert row['Spik'] == '1'
    assert row['Spiken var modellens förstaval'] is False
    assert row['Miss trots annat modellförstaval'] is True
    assert row['Modell p(spik)'] < .70


def test_small_sample_never_creates_spike_rule():
    s=spike_failure_summary([_coupon('c1',p=.70,hit=False)], min_review_spikes=100, min_review_coupons=20)
    assert s['review_ready'] is False
    assert s['status'] == 'SAMLA MER PROSPEKTIV SPIKHISTORIK'
    assert s['automatic_spike_threshold_change'] is False


def test_repeated_overconfidence_can_trigger_review_but_not_automatic_threshold():
    coupons=[]
    # 10 coupons around 60-65%, 10 around 70-75%, all misses => two mature overconfident bands.
    for i in range(10): coupons.append(_coupon(f'a{i}',p=.62,hit=False,market_p=.58))
    for i in range(10): coupons.append(_coupon(f'b{i}',p=.72,hit=False,market_p=.66))
    s=spike_failure_summary(coupons, min_review_spikes=100, min_review_coupons=20, min_band_matches=20, min_band_coupons=5)
    assert s['review_ready'] is True
    assert s['overconfident_bands'] >= 2
    assert s['status'] == 'GRANSKA SPIKÖVERKONFIDENS'
    assert s['automatic_model_change'] is False


def test_band_requires_match_and_coupon_breadth():
    rows=spike_band_rows([_coupon('one',p=.72,hit=False)], min_band_matches=10, min_band_coupons=2)
    band=next(r for r in rows if r['Intervall']=='70–75 %')
    assert band['Spikar'] == 13
    assert band['Kuponger'] == 1
    assert band['Moget segment'] is False
