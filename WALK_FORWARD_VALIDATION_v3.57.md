# Walk-Forward Strategy Validation – v3.57

## Syfte
Minska risken att samma prospektiva kuponghistorik både väljer och utvärderar en systemstrategi.

## Metod
För varje strategipar används endast kuponger där båda systemalternativen frystes före spelstopp, komplett facit finns och `captured_at` kan tolkas. Kupongerna sorteras i faktisk tidsordning.

1. De första 30 gemensamma kupongerna utgör träningshistorik.
2. Strategin med högst genomsnittligt antal täckta matcher väljs. Vid exakt lika resultat görs inget val.
3. Valet fryses och bedöms på nästa fulla block om 10 senare kuponger.
4. Därefter expanderar träningshistoriken med det avslutade blocket och processen upprepas.
5. Minst 20 senare testkuponger krävs för granskningsstatus.
6. Vinst/förlust för det i förväg valda systemet testas diagnostiskt med exakt tvåsidigt teckentest och Holm-korrigering över samtidiga strategipar.

## Viktiga begränsningar
Detta är starkare än att välja och mäta på samma historik, men det är inte ett formellt bevis på generalisering. Träningsregeln uppdateras över tid, testblock kan ligga i olika fotbollsmiljöer och kuponger är inte garanterat statistiskt oberoende. Ingen positiv signal tillåter automatisk strategiändring, ROI-påstående eller edge-påstående.
