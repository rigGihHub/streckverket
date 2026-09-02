from performance import VenueForm, shrink, venue_form_rating, home_away_form_signal, availability_signal, brier_score, multiclass_log_loss

def test_shrink_small_samples():
    assert abs(shrink(3.0,1,1.35)-1.5333333333)<1e-6

def test_good_home_form_beats_bad_away_form():
    h=VenueForm(10,8,1,1,22,7,.55); a=VenueForm(10,2,2,6,8,17,.55)
    assert venue_form_rating(h)>venue_form_rating(a)
    s=home_away_form_signal(h,a,'test')
    assert s.impact[0]>0 and s.impact[2]<0

def test_unconfirmed_absence_has_zero_strength():
    s=availability_signal(.4,.0,'forum',confirmed=False)
    assert s.effective_strength==0

def test_scores_reward_better_predictions():
    y=[0,2]
    good=[[.8,.1,.1],[.1,.1,.8]]; bad=[[.2,.4,.4],[.4,.4,.2]]
    assert brier_score(good,y)<brier_score(bad,y)
    assert multiclass_log_loss(good,y)<multiclass_log_loss(bad,y)
