# v3.86 – Counterfactual 13-Rätt Optimizer Audit

Syftet är att avgöra om Streckverket återkommande lämnar modellbaserad P(13) på bordet genom systemets struktur, inte genom för liten insats.

## Metodskydd
- Endast systemalternativ som redan frystes före match används.
- Kandidaten måste ha exakt samma radantal som originalsystemet.
- Bästa kandidat väljs endast efter fryst modell-P(13).
- Facit används enbart sekundärt efteråt och påverkar aldrig kandidatvalet.
- Minst 20 granskningsbara prospektiva kuponger krävs innan återkommande strukturell brist får pekas ut.
- Ingen automatisk ändring av `strategy_engine.py` eller `model_engine.py`.

Auditen klassificerar om förändringen främst är spik→gardering, gardering→spik, halv↔hel eller teckenbyte med oförändrad systemstorlek.
