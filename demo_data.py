from core import MatchInput, normalize

DEMO_MATCHES = [
    ("Arsenal", "Wolves", (1.42, 4.80, 7.20), (0.72,0.18,0.10), (0.68,0.20,0.12)),
    ("Blackburn", "Norwich", (2.45, 3.35, 2.90), (0.39,0.31,0.30), (0.40,0.29,0.31)),
    ("Everton", "Brighton", (2.62, 3.25, 2.72), (0.43,0.29,0.28), (0.37,0.30,0.33)),
    ("Leeds", "Coventry", (1.78, 3.75, 4.55), (0.64,0.22,0.14), (0.52,0.27,0.21)),
    ("Burnley", "Hull", (1.92, 3.50, 4.10), (0.49,0.29,0.22), (0.55,0.27,0.18)),
    ("Fulham", "Brentford", (2.20, 3.40, 3.25), (0.52,0.27,0.21), (0.44,0.29,0.27)),
    ("Sunderland", "Bristol City", (1.95,3.40,4.00), (0.47,0.30,0.23), (0.53,0.28,0.19)),
    ("Cardiff", "Watford", (2.85,3.25,2.50), (0.34,0.31,0.35), (0.30,0.29,0.41)),
    ("Derby", "Millwall", (2.38,3.10,3.15), (0.41,0.33,0.26), (0.42,0.31,0.27)),
    ("Preston", "QPR", (2.12,3.30,3.55), (0.50,0.28,0.22), (0.46,0.30,0.24)),
    ("Oxford", "Middlesbrough", (3.10,3.35,2.28), (0.28,0.29,0.43), (0.25,0.28,0.47)),
    ("Portsmouth", "Stoke", (2.55,3.20,2.80), (0.36,0.31,0.33), (0.38,0.30,0.32)),
    ("Swansea", "Sheffield Utd", (3.00,3.30,2.35), (0.31,0.29,0.40), (0.29,0.30,0.41)),
]

def get_demo_matches():
    out = []
    for i, (home, away, odds, public, model) in enumerate(DEMO_MATCHES, start=1):
        out.append(MatchInput(
            number=i,
            home=home,
            away=away,
            odds=tuple(odds),
            public=normalize(public),
            model=normalize(model),
        ))
    return out
