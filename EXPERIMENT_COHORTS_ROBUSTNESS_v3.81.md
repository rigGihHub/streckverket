# v3.81 – Experiment Cohorts & Robustness

Syfte: förhindra att ett bra totalresultat för en shadow-kandidat döljer systematisk svaghet i viktiga segment.

Fasta prospektiva kohorter:
- modellens förstaval: 1 / X / 2
- modellsäkerhet: <50 %, 50–60 %, 60–70 %, 70 %+ 
- största modell–marknad-gap: <2,5 pp, 2,5–5 pp, 5–10 pp, 10+ pp

Minst 30 färdiga matcher över 5 kuponger krävs per segment. Brier och log loss måste peka åt samma håll för positiv/negativ segmentbedömning. Funktionen är diagnostisk och ändrar aldrig produktion eller kandidatparametrar automatiskt.
