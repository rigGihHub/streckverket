# Streckverket v3.52 – Prospective Swap Backtest

## Syfte
Validera sida 558:s budgetomfördelning på ny data utan hindsight bias.

## Metod
När en riktig pre-match-snapshot sparas lagras upp till fem exakt visade omfördelningsförslag. Varje förslag bevarar donor/recipient, före/efter-tecken, radantal och den modellbaserade täckningsökning som beräknades före matcherna.

När komplett facit finns jämförs originalsystemets faktiska utfallstäckning med swap-systemets faktiska utfallstäckning. Primärförslaget (rank 1) används i den övergripande summeringen. Alternativen sparas för revision.

## Viktig metodspärr
Gamla facit-snapshots sparade inte låsningar eller vilket sida-558-förslag som faktiskt visades. De får därför inte rekonstrueras i efterhand. De ligger kvar som äldre historik utan swap-proveniens.

## Tolkning
- BÄTTRE UTFALLSTÄCKNING: swapen täckte fler av de 13 faktiska resultaten än originalsystemet.
- SÄMRE UTFALLSTÄCKNING: swapen täckte färre.
- OFÖRÄNDRAD UTFALLSTÄCKNING: lika många.
- Räddade 13: originalsystemet missade minst ett utfall men swap-systemet täckte alla 13.
- Tappade 13: originalsystemet täckte alla 13 men swapen gjorde det inte.

Minst 20 färdiga primära prospektiva förslag krävs innan verktyget ens lämnar statusen FÖR LITE PROSPEKTIV HISTORIK. Detta är en produktspärr, inte ett formellt statistiskt bevis på oberoende eller edge.

## Vad detta inte visar
Det visar inte ROI, förväntad utdelning, sann spelvinst eller bevisad edge. Det visar endast om den sparade omfördelningen historiskt hade täckt fler/färre faktiska matchutfall inom samma radbudget.
