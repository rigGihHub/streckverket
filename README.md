## v3.8.0 – Datadisciplin först
- Kuponger utan riktiga bookmakerodds markeras nu explicit med `market_available=False`.
- Den gamla tekniska 3,00–3,00–3,00-fallbacken får inte längre framstå som verklig marknadsdata i UI:t.
- Spelklarheten tvingas till VÄNTA när marknadsodds saknas för någon match.
- Externa odds som matchas säkert återställer normal marknadsstatus.

## v3.7.0 – Ett analysflöde
- Huvudfliken har nu en primär knapp: **Analysera kupongen**.
- Normalläget kräver inte att användaren hittar specialistfliken för multi-source-analys.
- Produktionsnycklar kan läsas från Streamlit Secrets (`THE_ODDS_API_KEY`, `FOOTBALL_DATA_API_KEY`, `API_FOOTBALL_KEY`) utan att visas i gränssnittet.
- Appen säger tydligt när externa lager saknas och använder bara verifierbara källor.


## v3.6.0 – Enklare huvudflöde
- Normalläge visar bara fem uppgiftsorienterade flikar: Vad ska jag spela?, Mitt system, Spikar, Fällor & skrällar och Varför?.
- Alla specialistverktyg finns kvar bakom Expertläge.
- Sidpanelen följer ett enkelt flöde: kupong först, budget därefter, rekommendation i huvudytan.
- Ingen analysmotor har tagits bort; komplexitet har flyttats bort från normalanvändarens väg.

# Streckverket v3.3.0 – Kunskapsmotorn

Streckverket är ett beslutsstöd för Stryktipset. Marknaden är basen, folkets streck är motståndaren och bara verifierad information får flytta sannolikheterna.

## Nytt i v3.0.0

- **Faktorfacit** sparas tillsammans med prognosen när en riktig multi-source-analys har körts.
- För varje verifierad modellfaktor sparas en **motberäkning utan just den faktorn**. Efter matchen kan Streckverket därför jämföra den faktiska modellen med samma modell där exempelvis hemmaform, lagstyrka eller skadeinformation hade utelämnats.
- `factor_learning.py` sammanställer per faktor:
  - antal matcher
  - hur ofta faktorn historiskt förbättrat Brier score
  - genomsnittlig Brier-förbättring
  - hur mycket faktorn i genomsnitt flyttat sannolikhetsmassan
  - antal registrerade källnamn
  - försiktig bedömning: För lite data / Ser lovande ut / Behöver granskas / Ingen tydlig skillnad
- Minst **30 faktorobservationer** krävs innan en faktor får en riktad bedömning.
- Först efter **100 observationer** kan appen visa ett granskningsförslag om en liten viktjustering bör testas.
- Modellvikter ändras **aldrig automatiskt**. Ett historiskt mönster är bara en hypotes som måste testas på ny separat data.
- Gamla v2.5–v2.9-facitfiler kan fortfarande importeras. De saknar faktorhistorik men går inte sönder.
- Resultatuppdatering bevarar sparade faktorobjekt och export/import av JSON bevarar hela kunskapsunderlaget.
- Facitfliken heter nu **Facit & lärande** och förklarar faktorfacitet på enkel svenska.

## Viktig metodprincip

Faktorfacitet mäter ett historiskt marginalbidrag: modellen med alla verifierade signaler jämförs mot en motberäkning där en signal i taget tas bort. Positiv förbättring betyder att sannolikheterna blev bättre för det observerade utfallet i just de historiska matcherna. Det bevisar inte att faktorn ensam orsakade förbättringen, eftersom faktorer kan samverka.

## Säkerhetsprinciper

- Ogranskade signaler lagras inte som aktiva faktorbidrag.
- Små urval får inte styra modellen.
- Historiska resultat är inte garanti för framtida kuponger.
- Ingen självlärande viktändring sker utan separat validering.
- Demodata får inte sparas som riktigt facit.

## Tidigare större steg

- v2.9.0: Omgångens spelplan
- v2.8.0: Var gör pengarna mest nytta?
- v2.7.0: Spelstrategen
- v2.6.0: Vad fungerar egentligen?
- v2.5.0: Facit och lärande historik
- v2.4.0: Förklarbar sannolikhetsmodell


## v3.2.0 – Lagringsmotor för växande historik

- Ny `history_store.py` med ett gemensamt lager för Streckverkets facit och kunskapsdata.
- SQLite fungerar direkt utan konto eller nycklar och upsertar kuponger/resultat säkert på `coupon_id`.
- PostgreSQL/Neon stöds via `STRECKVERKET_DATABASE_URL` (t.ex. Streamlit Secrets).
- Prognoser, importerade facit och automatiska/manuella resultat skrivs till lagringsmotorn när den är aktiv.
- JSON-import/export finns kvar som portabel säkerhetskopia och migrationsväg.
- Appen skiljer tydligt mellan lokal SQLite och verklig molnlagring; lokal Streamlit-disk kallas aldrig permanent.
- Databaslagret lagrar hela versionerade kupongsnapshoten som JSON så äldre historik kan fortsätta läsas när modellen utvecklas.


## v3.1.0 – Automatisk facitinhämtning
- Sparar avsparkstid i nya facit-snapshots.
- Kan hämta färdigspelade matcher via API-Football per sparat matchdatum.
- Registrerar bara 1/X/2 när båda lagnamnen matchar med hög säkerhet och matchstatus är slutspelad.
- Osäkra, pågående eller odaterade matcher lämnas orörda och kan fortfarande fyllas i manuellt.
- Gamla facitfiler utan kickoff fortsätter fungera men kräver manuell resultatinmatning.


## v3.3.0 – Kupongarkivet
- Ny flik **Kupongarkiv** som visar sparade kuponger i omvänd tidsordning.
- Filtrering på facitstatus och strategi samt sökning på kupong-ID/källa/lag.
- Öppna en gammal kupong och se system, modell/marknad/streck, facit och täckta tecken.
- Visar endast faktorhistorik som faktiskt sparades före match; fyller aldrig i gammal information i efterhand.
- Kupongspecifik jämförelse av Streckverkets och marknadsbasens Brier-fel när fullständigt facit finns.
- Arkivet är läsande och ändrar inte historiska prognoser.

## v3.4.0 – Modellcoach
- Samlar historiska modellsvagheter och styrkor i en egen coachvy.
- Prioriterar lägen där marknadsbasen historiskt slagit Streckverkets extra justeringar.
- Kombinerar situationsdiagnostik med faktorfacit.
- Kräver moget underlag innan slutsatser visas.
- Ändrar aldrig modellvikter automatiskt; viktförslag är endast kandidater för test på ny separat data.

## v3.5.0 – Poolvärdesmotorn
- Ny poolvärdesanalys som skiljer modellens systemtäckning från folkets streckmassa.
- Poolhävstång och pedagogiskt unikhetsindex; uttryckligen proxyer, inte utlovad/beräknad utdelning.
- Kupongrensare kräver både låg popularitet och rimligt sannolikhetsstöd; rena långskott premieras inte mekaniskt.
- Förbereder nästa steg: verklig utdelningsmodell när tillräcklig pool-/vinstdata finns.

## v3.10.0 – Verifieringsmotorn
- Jämför låsta historiska Streckverket-prognoser med bookmaker-marknaden på samma färdigspelade matcher.
- Brier och log loss används som huvudmått; träff på förstaval visas endast som komplement.
- Minst 100 verifierade matcher krävs innan en positiv skillnad ens får etiketten `LOVANDE EDGE`.
- Ett diagnostiskt 95 %-intervall visas för den parade Brier-skillnaden och senaste 30 % av historiken visas separat för att upptäcka försämring.
- Matcher som explicit saknar riktig marknadsbas (`market_available=False`) utesluts från benchmark.
- Verifieringsmotorn ändrar aldrig modellvikter automatiskt. Syftet är att försöka motbevisa att Streckverket tillför något utöver marknaden.
- Äldre facitfiler är bakåtkompatibla, men äldre historik saknar den explicita marknadstillgänglighetsflaggan och bör därför tolkas försiktigare.


## v3.10.0 – Produktionshärdning
- Kupongfingeravtryck kopplar analysresultat till exakt kupong/streck/marknadsunderlag.
- Gammalt multi-source-resultat rensas automatiskt om kupongen ändras.
- One-click-analys tidsmäts med verklig väggtid; appen visar senaste tiden så prestanda kan mätas före optimering.
- Ny ren hjälparmodul `production_hardening.py` och tester för state-integritet och timing.
- Ingen ny analysfaktor har lagts till; fokus är tillförlitlighet, regressionsskydd och mätbar prestanda.

## v3.13.0 – API- och cachekontroll
- Explicit TTL-cache för externa läsanrop i one-click-flödet.
- Kort TTL för odds, fixtures och lineups; längre TTL endast för stabilare metadata/form.
- Misslyckade API-anrop cachas aldrig.
- One-click-resultatet redovisar externa hämtningar och cacheträffar, så optimeringen kan mätas i stället för antas.
- Cache-nycklar inkluderar provider-/queryparametrar för att undvika sammanblandning mellan datakällor.

## v3.13.0 – gemensam analysorkestrering

- Normal- och expertflödet använder nu samma one-click-körväg via `analysis_controller.py`.
- Konfigurationsnormalisering för API-nycklar, sport keys, regioner och tävlingsgräns är centraliserad.
- Tidmätning och kupongfingeravtryck skapas på ett ställe i stället för duplicerad UI-kod.
- Prognosmodell, vikter och datakällornas innehåll är oförändrade.
- Syftet är mindre state-drift och säkrare fortsatt uppdelning av den stora Streamlit-filen.

## v3.15.0 – centraliserad kuponghämtning

- Ny `coupon_loader.py` är applikationens gemensamma gräns för Svenska Spel, CSV, demo och extern oddsberikning.
- `app.py` ansvarar inte längre för själva matchningen/ombyggnaden av kupongen vid extern oddshämtning.
- Oddsberikning använder `dataclasses.replace`, så kickoff, tävling och annan matchmetadata inte tappas när odds uppdateras.
- Matchad extern bookmakerdata sätter explicit `market_available=True`; om oddshämtningen misslyckas lämnas kupongen oförändrad.
- Ingen prognosvikt eller spelstrategi har ändrats i denna release.


## v3.15.0 – datatäckning och readiness-diagnostik
- Visar täckningsgrad per informationslager för den aktuella analyserade kupongen.
- Skiljer på att ett API svarar och att källan faktiskt matchar relevanta matcher/lag.
- Prioriterar den viktigaste aktuella dataluckan utan att kalla en källa historiskt dålig efter en enda körning.
- Marknadsodds behandlas fortsatt som kritiskt ankare: saknade riktiga odds blockerar spelklar status.
- Ingen prognosvikt, systemstrategi eller sannolikhetsmodell har ändrats.

## v3.16.0 – historisk datakvalitet

- Sparar datakvalitet efter genomförda riktiga one-click-analyser i `data/data_quality_history.json`.
- Demodata får inte sparas i denna historik.
- Historik summeras per extern källa med faktisk `matched/attempted`, felkörningar och försiktig bedömning.
- Källomdömen kräver minst tre kupongsnapshots innan Streckverket använder etiketter som stark/svag historisk täckning.
- Liga/tävling summerar readiness, svagaste informationslager och vilka verifierade signalkällor som faktiskt användes.
- Streckverket påstår inte per-liga-API-matchningsgrad ännu, eftersom nuvarande stages inte har matchnivåproveniens för detta.


## v3.17.0 – matchnivåspårning av datakällor

- One-click-analysen loggar nu källmatchning per match, inte bara totalsiffror för hela kupongen.
- Proveniens sparas för kupongkälla, The Odds API, football-data.org och API-Footballs fixture-matchning.
- Historikvyn kan aggreggera faktisk källmatchning per liga/tävling.
- Äldre historik räknas inte om eller fylls i med uppskattad matchnivådata. Exakt liga/källstatistik börjar därför först med v3.17-körningar.
- Källbedömningar kräver ett minsta antal faktiska matchningsförsök innan stark/svag etikett visas.
- Modellvikter, prognoslogik och systemstrategier är oförändrade.

## v3.18.0 – diagnos av datamissar
- Matchnivåproveniens har nu maskinläsbara `reason_code` för misslyckad datamatchning.
- Skiljer bland annat på saknad API-nyckel, API-fel, saknat matchdatum, tvetydig/låg lagnamnsmatchning och utebliven säker fixture-matchning.
- Historikvyn aggregerar felorsaker per källa och liga/tävling.
- Äldre fritextstatusar bakfylls inte med gissade kategorier; felorsakshistoriken börjar med v3.18-data.
- Ett problem kallas återkommande först efter minst tre observerade missar.


## v3.20.0 – Supporter Pulse-historik

- Ny `supporter_pulse_history.py` sparar tidsstämplade Supporter Pulse-snapshots före match med marknadsbas, liga, källa, underlagskvalitet och separata tonkomponenter.
- Demodata blockeras explicit från riktig supporterhistorik.
- Facit kan kopplas på först när ett riktigt 1/X/2-resultat finns; saknat facit gissas aldrig.
- Historisk utvärdering jämför signalen mot bookmakerförväntan (`faktisk vinst - marknadens vinstsannolikhet`) i stället för rå vinstprocent. Detta motverkar falsk edge från att favoritsupportrar både är optimistiska och ofta vinner.
- Separata grupper testas för hög självsäkerhet, uppgivenhet, oro, optimism samt stark positiv/negativ ton. Minst 30 observationer krävs innan ens en försiktig signalbedömning visas.
- Liga/tävling kan följas separat, men inga gamla snapshots bakfylls med påhittad Supporter Pulse-data.
- v3.20 ger **ingen automatisk modellvikt** till Supporter Pulse. Först historisk marginalnytta mot marknaden, därefter eventuell separat valideringsrelease.

## v3.19.0 – Supporter Pulse
- Supporterforum analyseras inte längre enbart som positiv/negativ sentiment.
- Ny experimentell `SupporterPulse` skiljer på självsäkerhet, uppgivenhet, oro, optimism och ilska.
- Mäter även konsensus, antal oberoende skribenter och förändring mot en angiven normalton/baslinje.
- Reddit-hämtningen sparar författare så att 30 inlägg från en person inte likställs med 30 oberoende röster.
- Supporter Pulse är i första hand radar/"undersök varför". Modellpåverkan är spärrad om signaltypen inte både är oberoende verifierad och historiskt validerad.
- Ingen befintlig prognosvikt eller systemstrategi har höjts i denna release.


## v3.21.0 – verifierade supporterkällor och liveinsamling
- Ny `supporter_sources.py` med explicit lagspecifik källkatalog. Okända lag/subreddits gissas aldrig fram.
- Reddit-adaptern hämtar bara från registrerade lagkällor, deduplicerar inlägg och filtrerar bort gammalt material.
- Inlägg efter matchstart blockeras från den pre-match Supporter Pulse som får sparas i historiken.
- Tidigare Supporter Pulse-snapshots kan användas som normalton först efter minst tre observationer från samma lag och källa.
- Expertläget kan hämta Supporter Pulse för alla registrerade lag på aktuell kupong och spara riktiga snapshots när bookmakerbas finns.
- `SUPPORTER_SOURCES_JSON` kan användas i Streamlit Secrets för att lägga till verifierade källor utan att ändra analysmotorn.
- Första inbyggda verifierade lagmappningen är Tottenham Hotspur → Reddit r/coys. Katalogen ska växa explicit, inte genom gissade subreddit-namn.
- Supporter Pulse har fortfarande 0 automatisk modellvikt.


## v3.22.0 – Supporter Source Expansion + relevansfilter
- Expanderar den explicita, manuellt verifierade Reddit-katalogen till Tottenham, Arsenal, Manchester United, Chelsea, Manchester City, Aston Villa och Everton. Okända lag gissas fortfarande aldrig.
- Inför ett konservativt relevansfilter före Supporter Pulse-analysen. Motståndare, match, startelva, skador, form, tränare och taktik höjer relevans; merchandise, nostalgi, memes, biljetter, fantasy och generellt transferbrus sänker den.
- UI visar andelen färska inlägg som bedömts matchrelevanta. Relevansfiltret verifierar aldrig fakta och Supporter Pulse har fortsatt 0 automatisk modellvikt.
