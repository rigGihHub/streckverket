from data_sources import parse_svenskaspel_api_payload, parse_svenskaspel_page_text


def fixture_event(n):
    return {
        "eventDescription": f"Hemma {n} - Borta {n}",
        "betMetrics": {"values": [
            {"odds":{"odds":"2,00"}, "distribution": 50},
            {"odds":{"odds":"3,50"}, "distribution": 28},
            {"odds":{"odds":"4,00"}, "distribution": 22},
        ]}
    }


def test_parse_api_requires_and_reads_13():
    payload={"draw":{"drawEvents":[fixture_event(i) for i in range(1,14)]}}
    coupon=parse_svenskaspel_api_payload(payload)
    assert len(coupon)==13
    assert coupon[0].home=="Hemma 1"
    assert coupon[0].away=="Borta 1"
    assert abs(sum(coupon[0].public)-1)<1e-12
    assert coupon[0].odds==(2.0,3.5,4.0)


def test_parse_page_text_13_matches():
    parts=[]
    for i in range(1,14):
        parts.append(f"{i}. {i} Hemma{i} - Borta{i} 1X2 Tipsinformation Svenska folket 50% 28% 22% Odds 2,00 3,50 4,00")
    coupon=parse_svenskaspel_page_text(" ".join(parts))
    assert len(coupon)==13
    assert coupon[-1].number==13
    assert coupon[-1].home=="Hemma13"
