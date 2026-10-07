# Streckverket v3.61 – Prospective Late-Market Benchmark

## Syfte

v3.60 kunde jämföra en marknadsbild med den senaste verifierade förmarknaden i den aktuella tidslinjen. v3.61 gör detta prospektivt utvärderingsbart över sparad historik.

## Ny proveniens

Varje ny `FacitCoupon` sparar `market_timeline_key`. Det är en explicit länk till den marknadstidslinje som hör till exakt samma fixture-set.

Äldre kuponger utan nyckeln exkluderas. Nyckeln rekonstrueras inte i efterhand.

## Senare marknadspunkt

En observation kräver att bookmakerpunkten:

- hör till samma explicit länkade tidslinje,
- gäller samma matchnummer,
- är verifierad som tillgänglig marknad,
- är tidsstämplad strikt **efter** prognossnapshoten,
- ligger **före eller vid** avspark.

Den marknadspunkt som automatiskt sparas samtidigt med prognosen räknas därför inte som en senare observation.

## Vad mäts?

För varje prospektiv observation mäts bland annat:

- initialt modell–marknad-gap,
- senaste lagrade verifierade bookmakerpunkt före avspark,
- tid mellan den punkten och avspark,
- största bookmakerförflyttning i procentenheter,
- om total variation-distance mellan marknaden och den frysta modellen minskade eller ökade.

Segmenteringen använder redan frysta gapgränser:

- LÅGT GAP ≤ 4 pp
- NORMALT GAP 4–8 pp
- HÖGT GAP ≥ 8 pp

## Granskningsgräns

Varje gapgrupp kräver minst:

- 100 matcher
- 20 separata kuponger

innan status blir `GRANSKNINGSBAR`.

## Viktig begränsning

Marknadsrörelse mot modellen är **inte** matchfacit, positiv EV, ROI eller bevisad edge. Benchmarken ändrar inga modellvikter och inga systemstrategier automatiskt.

## Predictive change

`predictive_change=False`.
