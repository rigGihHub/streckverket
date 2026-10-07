# Streckverket v3.89.0 – Reliable Start

[Öppna Streckverket i webbläsaren](https://streckverket.streamlit.app/).
Adressen avser befintlig publicerad app; versionsnumret som visas i appen avgör vilken kod som körs. Om appen har somnat visas en knapp för att väcka den.

## v3.89.0

- **Analysera kupongen** är synlig direkt efter att en riktig kupong har öppnats. Uppdateringsknappen ligger också utanför den hopfällda diagnostiken.
- Hämtning och analys visar laddningsindikatorer.
- Startsidan erbjuder CSV-import som reserv om Svenska Spels kupong inte går att hämta.
- CSV öppnas först med ett explicit knapptryck. Kvarliggande uppladdning orsakar inte längre en omladdningsloop, och ogiltiga filer ger ett felmeddelande.
- Om riktig kupong inte kan hämtas från testläget avbryts analysen och testkupongen förblir testdata.
- Prognos- och strategimotorerna är oförändrade.

Se `RELIABLE_START_v3.89.md`.

# Streckverket v3.86.0 – Counterfactual 13-Rätt Optimizer Audit

## v3.86.0

Ny prospektiv audit som jämför originalsystemet mot redan frysta alternativ med exakt samma radantal och identifierar strukturellt P(13)-headroom mellan spikar, halv- och helgarderingar. Facit används aldrig för att välja alternativ. Se `COUNTERFACTUAL_13_OPTIMIZER_AUDIT_v3.86.md`.

# Streckverket v3.85.0 – Guard Allocation Lab

## v3.85.0

Ny prospektiv Guard Allocation Lab. Den jämför endast före-match frysta alternativ med exakt samma radantal som originalsystemet för att isolera garderingarnas placering från större insats. Facit används endast sekundärt och ingen strategi ändras automatiskt. Se `GUARD_ALLOCATION_LAB_v3.85.md`.

# Streckverket v3.83.0 – System P(13) Audit


## v3.83.0

Ny prospektiv System P(13) Audit. Den jämför originalsystemet med systemalternativ som redan frystes före match under samma budget och låsningar. Äldre kuponger rekonstrueras inte. Facit används bara sekundärt efter att systemen varit låsta. Se `SYSTEM_P13_AUDIT_v3.83.md`.

## v3.82.0

- Windows kan nu starta appen genom dubbelklick på `STARTA_STRECKVERKET.bat`; ingen PowerShell-kommandorad behövs.
- Dockerfile + Render Blueprint + Streamlit serverconfig gör projektet redo för publicerad webbdrift.
- Lokala databaser och secrets exkluderas från Git/Docker.
- Riktig serverdrift ska använda `STRECKVERKET_DATABASE_URL` för beständig prospektiv historik; ephemeral SQLite får inte behandlas som beständig data.
- Appens versionsrad hämtas nu från `release_info.py` i stället för den gamla hårdkodade v3.75-texten.
- Ingen ändring av `model_engine.py` eller `strategy_engine.py`.

Se `DEPLOYMENT_READY_v3.82.md`.

# Streckverket v3.79.0 – Shadow Experiment Governance & Promotion Gate

## v3.79.0

Lägger ett konservativt governance-lager ovanpå v3.78 shadow mode. Kandidater kan förkastas, fortsätta samla data eller bli godkända för separat manuell produktionskandidat-granskning. Ingen automatisk promotion och inga ändringar i prognos- eller strategimotorn.

Se `SHADOW_EXPERIMENT_GOVERNANCE_v3.79.md`.

## v3.78.0 – Predictive Experiment Framework
- Nytt prospektivt **shadow mode** mellan v3.77:s beslutsgrind och en eventuell framtida produktionsändring.
- Kandidatprognosen fryses före facit tillsammans med ordinarie modell och bookmakerankare.
- Första förhandsregistrerade kandidaten är `market_pull_25_v1`: 75 % produktionsmodell + 25 % verifierat bookmakerankare, endast när v3.77-grinden öppnar för just detta experiment.
- Kandidat, produktion och marknad jämförs på exakt samma shadow-observationer med Brier score och log loss.
- Minst 100 färdiga shadow-matcher över 10 kuponger krävs före mogen bedömning.
- Ingen historisk backfill och ingen automatisk promotion till produktion.
- `model_engine.py` och `strategy_engine.py` är oförändrade.

# Streckverket v3.77.0 – Market Anchor Decision Lab

## v3.77.0 – Market Anchor Decision Lab
- Ny `market_anchor_decision.py` sammanför modell-vs-marknad, signalablation och avvikelsesegment i en konservativ beslutsgrind.
- Fasta samplekrav avgör när resultat överhuvudtaget får motivera ett separat prediktivt experiment.
- Om marknaden är bättre på både Brier och log loss pekar labbet mot ett separat experiment närmare marknadsankaret – aldrig en automatisk produktionsändring.
- Om modellen är bättre krävs även mogen positiv signalablation innan en specifik signal pekas ut som kandidat.
- Stora modellavvikelser som underpresterar marknaden flaggas separat.
- `model_engine.py` och `strategy_engine.py` är oförändrade.

## v3.76.0 – Model vs Market & Signal Ablation Lab
- Ny `model_market_validation.py`: parad Brier/log loss mellan fryst Streckverket-modell och verifierat bookmakerankare på exakt samma matcher.
- Visar modellens vinst/förlust mot marknaden och segmenterar efter hur långt modellen faktiskt avvek från marknadsankaret.
- Ny `signal_ablation.py`: leave-one-signal-out på prospektivt frysta, verifierade faktorsnapshots.
- En signal får inte bedömas som mogen utan både minsta antal observationer och spridning över flera kuponger.
- Ingen automatisk modell-/viktändring; `model_engine.py` och `strategy_engine.py` är oförändrade.


Fokus flyttas från UX till själva 13-rätt-målet. Ett nytt prospektivt labb visar varför kompletta sparade kuponger missade 13: spikmiss, halvgarderingsmiss, prognosfel eller fall där modellens förstaval var rätt men systemet ändå valde bort utfallet. Minst 20 kompletta kuponger krävs innan labbet får peka ut vilken motor som bör granskas. Inga modell- eller strategiändringar görs i denna release.

## v3.73.0 – Key Coupon Decisions

- Lyfter **VIKTIGASTE SPIKEN**, **VIKTIGASTE GARDERINGEN** och, när datan stödjer det, **MATCHEN SOM KAN FÄLLA MÅNGA**.
- Bygger enbart på systemets redan valda tecken samt befintliga modell- och streckprocent.
- Visar högst tre beslut för att behålla normalvyn snabb och lättläst.
- Ingen förändring av prognosmodell, strategi eller systemoptimering.

## v3.72.0 – Why the System Changed

- Visar **Varför ändrades systemet?** när en omanalys byter tecken.
- Kopplar varje ändrad match till observerade samtidiga förändringar i odds, streckfördelning, modellsannolikheter och verifierat lagunderlag.
- Skiljer lokal dataändring från global budgetomfördelning över hela kupongen.
- Om ingen synlig orsak kan fastställas säger Streckverket det uttryckligen i stället för att hitta på en förklaring.
- Diagnostisk UX-förbättring; ingen prognos- eller strategiförändring.

## v3.71.0 – Analysis Change Report

- Visar **Vad ändrades sedan förra analysen?** direkt efter manuell omanalys.
- Tydligt huvudbesked: **SYSTEMET ÄR OFÖRÄNDRAT** eller **SYSTEMET ÄNDRADES I N MATCHER**.
- Detaljer kan visa systemövergångar, ändrade odds, förbättrat startelvsunderlag och readiness-status.
- Diagnostisk UX-förbättring; ingen prognos- eller strategiförändring.

# Streckverket v3.68.0

**Actionable Readiness Guidance** – normalvyn säger nu inte bara REDO/VÄNTA utan vad användaren faktiskt ska göra härnäst. Datakvalitetspoängen ligger sekundärt och får inte misstolkas som vinstchans.

# Streckverket v3.65.0 – Single-Screen Novice Flow

- Normalvyn är nu ett enda sammanhängande beslutsflöde utan dubbla tabs.
- `Mitt system`, `Spikar`, `Fällor & skrällar` och den separata `Varför?`-fliken är expertmaterial; nybörjaren får samma kärnsvar direkt på huvudytan.
- Expertläge behåller detaljnavigationen.
- Automatisk pre-kickoff-marknadsinsamling är frikopplad från tabbnavigationen och fortsätter samla prospektiv data passivt.
- Ingen prognos- eller strategimotor har ändrats.

# Streckverket v3.60.0 – Verified Pre-Kickoff Market Quality

Ny prospektiv validering av bookmaker-oenighet. Endast snapshots från v3.58+ med faktiskt sparad bookmaker-spridning används. HÖG/NORMAL/OENIG marknad jämförs mot modellens och marknadens Brier/log loss/förstaval, med krav på minst 100 matcher och 20 separata kuponger per miljö. Ett explorativt modellgap × marknadsmiljö-rutnät använder fasta gränser och får inte ändra modellen automatiskt.

# Streckverket v3.58.0 – Walk-Forward Strategy Validation

- Strategipar utvärderas nu i faktisk tidsordning från sparad `captured_at`; kupong-ID används aldrig som ersättning för kronologi.
- Minst 30 äldre gemensamma prospektiva kuponger väljer den historiskt starkare strategin. Valet fryses och testas på nästa fulla block om 10 senare kuponger.
- Efter varje testblock expanderar träningshistoriken och nästa framtida block utvärderas utan att dess facit har påverkat det tidigare valet.
- Träningsmässigt oavgjort strategipar ger inget påtvingat val och bidrar därför inte med efterhandsriktning.
- Minst 20 verkligt senare testkuponger krävs innan ett strategipar blir walk-forward-granskningsbart.
- Parvisa senare utfall får ett exakt teckentest och Holm-korrigering över samtidiga strategipar.
- Positiv walk-forward-signal innebär fortfarande inte ROI, bevisad edge, kausalitet eller formellt oberoende out-of-sample-bevis.
- Prognos- och ordinarie strategimotor är oförändrade.

# Streckverket v3.56.0 – Strategy Confidence Guard

- Strategier jämförs parvis bara på kuponger där båda systemen faktiskt frystes före spelstopp.
- Minst 20 gemensamma färdigspelade kuponger krävs för att ett strategipar ska bli `GRANSKNINGSBAR`.
- Ligapoäng ges endast från sådana kvalificerade möten; för liten gemensam historik ger inga poäng.
- Identiska system dedupliceras fortfarande fysiskt, men v3.54 bevarar strategialias så identiska strategier räknas som verkliga oavgjorda möten.
- Äldre alias gissas inte. Endast den explicit sparade faktiska strategin kan säkert återkopplas till `ORIGINAL`.
- Tabellen mäter faktisk systemtäckning och 13-rättstäckning, inte ROI, utdelning eller bevisad edge.
- Prognos- och strategimotor är oförändrade.

# Streckverket v3.53.0 – Counterfactual System Lab

- Nya riktiga pre-match-facit sparar upp till fem faktiska sida-558-omfördelningsförslag tillsammans med snapshoten.
- Förslagen innehåller exakt donor/recipient, före/efter-tecken, radantal och den förväntade täckningsökning som beräknades före match.
- När alla 13 resultat finns utvärderas primärförslaget mot originalsystemet med exakt samma radantal.
- Facit visar bättre/lika/sämre faktisk utfallstäckning samt om swapen räddade eller tappade 13-rättstäckning.
- Äldre snapshots backfylls aldrig: de saknar historiska låsningar och uppgift om vilket förslag som faktiskt visades.
- Minst 20 färdiga primära prospektiva förslag krävs innan status kan gå vidare från `FÖR LITE PROSPEKTIV HISTORIK`.
- Funktionen mäter inte ROI, utdelning eller bevisad edge. Prognos- och strategimotor är oförändrade.

# Streckverket v3.49.0 – Text-TV Decision Compression

- Normalvyn har nu en sammanhängande Text-TV-navigation: **100 Start, 551 System, 552 Matchråd, 553 Spikar, 554 Fällor, 555 Skrällar och 556 Datastatus**.
- Sidorna återanvänder exakt samma system, klassificeringar och readiness som resten av appen; de skapar inga nya prognoser eller egna spelregler.
- Sida 556 skiljer uttryckligen datakvalitet från prognossäkerhet och visar verifierad bookmaker-täckning.
- Text-TV-layouten är mobilanpassad med kantiga block, monospace och klassiska gul/cyan/grön/blå informationsytor.
- Presentationsbugg i taggningen rättad: befintliga `Fällan`/`Skrälläge`-klassificeringar visas nu korrekt på systemtavlan.
- Modell- och strategimotor är oförändrade.

# Streckverket v3.47.0 – Text-TV 551

- Normalvyn har nu en riktig Text-TV-inspirerad systemtavla, sida 551.
- Alla 13 matcher visas kompakt med 1/X/2 och SPIK/GARD/HELGARD.
- Sida 552 ger korta telegram baserade enbart på befintlig modell- och streckdata.
- Ingen modell- eller strategiändring; presentationen är separerad i `texttv_view.py`.
- Mobil CSS behåller fem tydliga kolumner utan moderna kort.

# Streckverket v3.43.0


## v3.53.0 – Counterfactual System Lab
- Sparar upp till fem faktiska sida-558-omfördelningsförslag i facit-snapshoten före spelstopp.
- Primärförslaget utvärderas först när alla 13 resultat finns.
- Jämför faktisk utfallstäckning med originalsystemet vid exakt samma radantal.
- Äldre snapshots saknar swap-proveniens och backfylls aldrig i efterhand.
- Minst 20 färdiga primära prospektiva förslag krävs innan status kan bli mer än `FÖR LITE PROSPEKTIV HISTORIK`.
- Ingen ROI-, utdelnings- eller edge-slutsats dras av swap-backtestet.

## v3.43.0 – Product Reality Check

- Historisk modellvalidering kräver nu både minst 100 verifierade matcher och minst 20 separata kuponger innan ett positivt mönster får lyftas.
- `LOVANDE EDGE` har ersatts av den försiktigare etiketten `LOVANDE MÖNSTER`; detta är fortfarande inte bevisad edge.
- Positivt mönster kräver även att Brier-fördelen är positiv i den nyare 30 %-delen av historiken.
- Nya facit-snapshots sparar `model_version`; äldre historik utan versionsmetadata lämnas som okänd.
- Ny `validation_reality.py` och UI-sektion **Produktens verklighetskontroll** visar oberoende kupongbredd, datakvalitet och versionsproveniens.
- Modell- och strategimotor är oförändrade.

## v3.41.0 – App Shell Refactor III + Runtime Smoke Harness

- Bröt ut `Databerikning` från `app.py` till `ui_data_enrichment.py`.
- `app.py` minskad från cirka 1 229 till 1 054 rader utan ändringar i modell- eller strategimotor.
- Lade till `runtime_smoke.py` med Streamlits `AppTest` för tre skalnivåer: normal, expert och specialist.
- Smoke-harnessen trycker inte på externa API-knappar och ska därför kunna köras deterministiskt i CI/deploymiljö med `requirements.txt` installerad.
- I denna byggmiljö saknas Streamlit-paketet; de tre riktiga AppTest-testerna skippar därför explicit i stället för att rapportera falskt grönt.
- Ingen modellvikt, prognosregel, systemstrategi eller evidensregel har ändrats.

### Verifiering

Verifiering: 326 pytest PASS, 3 runtime-smoketester SKIPPED eftersom Streamlit inte finns installerat i byggmiljön. Python-kompilering och ZIP-integritet verifieras vid paketering. `model_engine.py` och `strategy_engine.py` jämförs byte-för-byte mot v3.40.0.

---

# Streckverket v3.40.0

## v3.40.0 – App Shell Refactor II

- Bröt ut `Vad ska jag spela?` till `ui_decision_page.py`.
- Bröt ut `Datagranskning` till `ui_data_review.py`.
- Bröt ut `Information Edge` till `ui_information_edge.py`.
- `app.py` minskad till cirka 1 230 rader utan ändringar i modell- eller strategimotor.
- Fixade en runtime-risk där `CouponReadiness` användes utan explicit import när riktiga marknadsodds saknas.
- Inga nya edge-påståenden eller modellvikter.


## App Shell Refactor + Error Boundary Hardening

- `Facit & lärande` är utbrutet från `app.py` till `ui_facit.py`.
- `Kupongarkiv` är utbrutet till `ui_coupon_archive.py`.
- `app.py` har minskat från cirka 2 450 till cirka 1 670 rader utan ändring i prognos- eller strategimotor.
- Intern datumparsning och poolvärdesberäkning använder nu specifika felgränser i stället för bred `except Exception`.
- Misslyckad extern tabellhämtning degraderar fortsatt säkert, men felet är inte längre helt tyst i UI:t.
- Externa I/O-gränser behåller defensiv felhantering där ett leverantörsfel inte ska krascha hela appen.
- Ingen modellvikt, prognosregel, systemstrategi eller evidensregel har ändrats.

### Verifiering

Verifiering: 320/320 pytest PASS. Python-kompilering OK. `model_engine.py` och `strategy_engine.py` är byte-identiska med v3.38. ZIP-integritet verifieras vid paketering. Streamlit runtime/UI är inte visuellt verifierad i deploymiljö.

---

# Streckverket v3.36.0

## Expert UX Cleanup

- Expertläget visar nu en kuraterad huvudväg i stället för alla specialistflikar samtidigt.
- Primära expertflikar: Datagranskning, Information Edge, Facit & lärande, Kupongarkiv och Modellcoach.
- Lågfrekventa verktyg finns kvar bakom **Visa specialistverktyg** i sidpanelen.
- Expertflödet i sidpanelen förklarar ordningen: datakvalitet → evidens → lärande.
- Ingen prognosmodell, systemstrategi eller evidensregel har ändrats.
- Normalflödet är oförändrat.

# Streckverket v3.35.0

## v3.35.0 – Evidence Dashboard & Data Sufficiency

### Nytt i v3.35.0

- Samlar upprepad signalevidens och riktningsanalys i en gemensam evidensöversikt.
- Segment prioriteras efter datamängd, antal unika matcher och proveniens – inte efter en hög procentsiffra på tunt underlag.
- Statusar: `GRANSKA NU`, `GRANSKA TIDSMÖNSTER`, `FIXA PROVENIENS` och `SAMLA MER DATA`.
- Segment med okänd liga eller källa lyfts som datakvalitetsproblem i stället för att blandas in i namngivna segment.
- Dashboarden visar exakt hur många observationer och unika matcher som saknas före granskningsnivån.
- `GRANSKA NU` betyder endast att underlaget är tillräckligt för manuell analys. Det tillåter inte edge-påstående, kausalitet eller automatisk modellviktsändring.

### Metodprincip

Dashboarden är en granskningskö, inte en signalranking. Ett segment med mycket hög andel marknadsrörelse i samma riktning får inte hög prioritet om underlaget är litet eller proveniensen är oklar. Datatillräcklighet kommer före effektstorlek.

### Verifiering

- 308 / 308 tester passerar.
- Streamlit runtime/UI är inte visuellt verifierad i deploymiljö.

---

## v3.34.0 – Signal Direction & Market Response

### Nytt i v3.34.0

- Verifierade modellfakta sparar nu sin faktiska `EvidenceSignal.impact` för 1/X/2 som riktningsproveniens.
- Riktningsanalys görs endast när faktumet var **säkert verifierat före** marknadens observerade rörelseintervall.
- Marknadsrespons klassificeras som **SAMMA RIKTNING**, **MOTSATT RIKTNING** eller **BLANDAD/OKLAR RIKTNING** utifrån den sparade signalvektorn och den observerade marknadsförändringen.
- Äldre historik utan sparad impact-vektor får **RIKTNING OKÄND** och används inte som riktningsbevis.
- Evidens aggregeras separat per signaltyp, liga och källa och kräver minst **30 riktningsobservationer + 20 unika matcher** innan segmentet ens får status TILLRÄCKLIGT FÖR GRANSKNING.
- Varken edge- eller orsakspåståenden tillåts av analysen. Inga modellvikter ändras.

### Metodprincip

Streckverket gissar inte att exempelvis en skada automatiskt ska sänka ett visst lag. Riktningen måste komma från den verifierade signalvektor som faktiskt användes i modellen. Marknadens rörelse jämförs därefter geometriskt med samma 1/X/2-riktning. Att de rör sig åt samma håll visar endast samstämmighet i efterföljande observerad marknadsrespons – inte att signalen orsakade rörelsen eller att signalen har prediktiv edge.

### Verifiering

- 303 / 303 tester passerar.
- Streamlit runtime/UI är inte visuellt verifierad i deploymiljö.

---

# Streckverket

## v3.33.0 – Repeated Signal Evidence

### Nytt i v3.33.0
- Upprepad Fact → Market-evidens analyseras över hela lagrade historiken, inte bara aktuell kupong.
- Segment hålls strikt isär per signaltyp, liga och källa.
- Ett segment kräver minst 30 observationer **och** 20 unika matcher för status `TILLRÄCKLIGT FÖR GRANSKNING`.
- Flera datapunkter från samma match kan inte ensamma skapa evidens.
- Osäker tidsordning räknas aldrig som att faktumet kom före marknaden.
- Äldre signaler utan ligaproveniens märks `Okänd liga` och blandas inte med namngivna ligor.
- Nya verifierade fakta får ligaproveniens från den faktiska kupongmatchen när sådan finns.
- Ingen segmentstatus tillåter edge-påstående eller automatisk modellviktsändring.

### Metodprincip
30 blandade observationer från olika ligor eller källor är inte 30 observationer av samma fenomen. v3.33 kräver homogen historik innan ett mönster ens får granskas.

## v3.32.0 – Fact → Market Timing Analysis

### Nytt i v3.32.0

- Jämför endast **VERIFIERAD MODELLSIGNAL** mot verifierad bookmaker-tidslinje.
- Använder `verified_at`, inte första observationstid, när ett faktum jämförs med marknaden.
- Lokaliserar första marknadsrörelsen till ett **intervall mellan två snapshots** i stället för att hitta på en exakt rörelsetid.
- Klassificerar tidsrelation som **SÄKERT FÖRE RÖRELSEINTERVALL**, **INOM OSÄKERT RÖRELSEINTERVALL** eller **EFTER OBSERVERAD RÖRELSE**.
- Kräver minst **30 observationer** innan ett återkommande mönster ens får status *TILLRÄCKLIGT FÖR GRANSKNING*.
- Statusen tillåter aldrig automatiskt edge-påstående; analysen är diagnostisk och ändrar inga modellvikter.


Streckverket skiljer nu på observerad supporterton, direkt leverantörsuppgift och verifierad modellsignal på samma tidsaxel. För skador/frånvaro och bekräftade startelvor sparas när Streckverket faktiskt behandlade uppgiften (`observed_at`) och när appen accepterade den på sin uttryckliga verifieringsnivå (`verified_at`). Dessa tider ersätts inte med antagna publiceringstider.

API-Football-observationer bevarar direkt källa, confidence och independence group. En enda strukturerad API-källa uppgraderas inte automatiskt till oberoende bekräftelse. Startelvor kan därför visas som `LEVERANTÖRSBEKRÄFTAD` utan automatisk modellpåverkan, medan en redan verifierad skade-/frånvarosignal kan visas som `VERIFIERAD MODELLSIGNAL` när den faktiskt ingår i modellens auditerade signaler.

Observationstiden fångas redan vid analysögonblicket och hålls i sessionen tills den gemensamma historiklagringen är tillgänglig. SQLite/PostgreSQL använder den befintliga flexibla `signal_points`-payloaden, och äldre v3.30-poster utan `observed_at`/`verified_at` kan fortfarande läsas.

Ingen ny prognosvikt eller systemstrategi har införts. Verified Fact Timeline är provenance-/historikinfrastruktur och får inte tolkas som bevis på att en signal har prediktiv edge.

## v3.30.0 – Signal Timeline Foundation

Streckverket har nu en gemensam, tidsstämplad grund för externa signaler och bookmaker-marknad. Varje signalpunkt lagrar match, tid, signaltyp, ämne, källa, verifieringsstatus, upstream-proveniens, om signalen får påverka modellen samt en typ-specifik payload.

Första verkliga integrationen är Supporter Pulse. Befintliga supporterobservationer kan projiceras till den gemensamma tidsaxeln men märks uttryckligen som `observerad_ton` och `model_usable=False`. Supporterton blir alltså inte ett verifierat skade-, startelvs- eller nyhetsfaktum genom migreringen.

SQLite och PostgreSQL har fått en separat `signal_points`-tabell med stabil identitet och deduplicering. Marknadspunkterna ligger kvar i sin egen tabell, men UI kan nu visa marknad och externa signaler på samma kronologiska tidslinje. Detta skapar infrastrukturen för senare analyser av vad som observerades före/efter en marknadsrörelse utan att påstå kausalitet.

Ingen prognosvikt, systemstrategi eller bookmakerbas har ändrats. Nyheter/skador/startelvor läggs inte automatiskt in i tidslinjen förrän de kan få korrekt tidsstämpel, källa och verifieringsstatus.

## v3.8.0 – Datadisciplin först

## v3.29.0 – Market Movement Intelligence

- Klassificerar verifierad marknadsrörelse som STABIL, MÅTTLIG RÖRELSE eller KRAFTIG RÖRELSE.
- Visar vilket av 1/X/2 som haft störst nettoförändring mellan första och senaste verifierade marknadspunkt.
- Kopplar sparad Supporter Pulse tidsmässigt till den första **observerade** marknadsrörelsen när sådan jämförelse faktiskt kan göras.
- Påstår inte att Supporter Pulse orsakar rörelsen eller har prediktiv edge.
- Påstår inte att rörelsetidpunkten är exakt: marknaden kan ha flyttat när som helst mellan två sparade snapshots.
- Nyhetskoppling är medvetet inte byggd ännu eftersom tidsstämplad nyhetshistorik saknas i nuvarande datamodell.

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




## v3.24.0 – Validation Eligibility Gate
- Modell-vs-marknad-historik räknar endast färdigspelade matcher där `market_available=True` uttryckligen sparats.
- Gamla facitposter utan explicit marknadsproveniens behandlas konservativt som ej verifierbara i stället för att antas ha riktig bookmakerbas.
- Samma spärr används för aggregerad prestanda, kalibrering, segmentdiagnostik, faktorutvärdering och benchmark.
- UI visar hur många färdiga matcher som exkluderats på grund av saknad/oklar bookmakerbas.
- Systemets faktiska 13-rättstäckning behålls separat från modellvalideringen.

## v3.23.0 – Supporter Pulse Source Independence

- Reddit-insamlingen behåller extern destinationslänk när ett inlägg länkar vidare till en artikel.
- Spårningsparametrar tas bort innan källursprung jämförs.
- Flera forumtrådar som bygger på samma externa artikel räknas som ett gemensamt upstream-ursprung.
- Egna forumdiskussioner behandlas fortfarande som separata supporterreaktioner; Reddit-permalänkar misstolkas inte som externa nyhetskällor.
- Supporter Pulse visar antal oberoende ursprung, källoberoendegrad och hur stor andel som kommer från största ursprunget.
- Källoberoende sparas i Supporter Pulse-historiken (schema v2) så att framtida validering kan skilja bred supporterreaktion från ekon av samma nyhet.
- Ingen supporterdata får fortfarande automatisk modellvikt.

## v3.22.0 – Supporter Source Expansion + relevansfilter
- Expanderar den explicita, manuellt verifierade Reddit-katalogen till Tottenham, Arsenal, Manchester United, Chelsea, Manchester City, Aston Villa och Everton. Okända lag gissas fortfarande aldrig.
- Inför ett konservativt relevansfilter före Supporter Pulse-analysen. Motståndare, match, startelva, skador, form, tränare och taktik höjer relevans; merchandise, nostalgi, memes, biljetter, fantasy och generellt transferbrus sänker den.
- UI visar andelen färska inlägg som bedömts matchrelevanta. Relevansfiltret verifierar aldrig fakta och Supporter Pulse har fortsatt 0 automatisk modellvikt.

## v3.25.0 – Observation Quality Score

Historiska matchobservationer får nu en separat datakvalitetsbedömning som beskriver hur starkt underlaget var när prognosen sparades. Bedömningen påverkar inte 1/X/2-modellen och används inte för att automatiskt radera eller skriva om historik.

Kvalitetsmåttet använder endast metadata som faktiskt finns:

- verifierad bookmakerbas
- explicit marknadskälla
- antal bookmakers i marknadsbasen
- oddsens färskhet vid sparning
- säkerheten i oddsens matchning mot kupongmatchen
- hur nära avspark prognosen sparades
- streckens färskhet när sådan tidsstämpel faktiskt finns.

Saknad metadata ger inga påhittade poäng och redovisas som saknat underlag. Äldre historik kan därför få lägre kvalitetspoäng utan att observationen i sig behöver ha varit dålig.

The Odds API-proveniens som redan finns vid insamling följer nu med in i facithistoriken: bookmakerantal, senaste oddsuppdatering och säker matchning sparas per match. Svenska Spel- och CSV-marknad får explicit källproveniens när riktiga odds finns, men Streckverket hittar inte på bookmakerantal eller färskhet om dessa uppgifter saknas.

Benchmarken kan nu köras med ett explicit minsta kvalitetspoäng för diagnostisk jämförelse. Standardbenchmarken är oförändrad och använder fortfarande alla verifierade bookmakerobservationer. UI visar därför både historikens datakvalitet och hur många verifierade matcher som når minst 60/100, utan att göra ett nytt edge-påstående.

Verifiering för v3.25.0:

- 259 / 259 pytest-tester passerar
- observation-quality-specifika tester ingår
- Python-kompilering verifieras före release
- ZIP-integritet verifieras före release
- Streamlit runtime/UI har inte visuellt verifierats i deploymiljö

## v3.26.0 – Capture Quality Gate

Facithistoriken får nu en kontroll före sparning. Syftet är att förbättra framtida modellvalidering genom att stoppa observationer som inte längre är rena pre-match-snapshots eller som saknar verifierad bookmakerbas för någon av kupongens 13 matcher.

Kontrollen visar före sparning:

- status: BRA, GODKÄND, SVAG, VÄNTA eller SPARA INTE
- genomsnittlig observationskvalitet 0–100
- verifierad bookmakerbas x/13
- hur stor del av kvalitetsmetadata som faktiskt finns
- konkreta åtgärder för att förbättra underlaget.

Hårda integritetsregler:

- exakt 13 matcher krävs
- om någon match med känd avspark redan har startat spärras pre-match-sparning
- verifierad bookmakerbas krävs för samtliga 13 matcher innan facitsnapshot får sparas
- demo får fortfarande aldrig sparas som riktig historik.

Svag metadata är däremot inte automatiskt ett sparförbud om alla 13 bookmakerbaser är verifierade och kupongen fortfarande är pre-match. Snapshoten kan då sparas med låg kvalitetsklass så att historiken inte förskönas i efterhand.

Capture Quality Gate använder bara dataproveniens och timing. Den tittar inte på vilket lag modellen föredrar, systemets tecken eller framtida resultat och kan därför inte skapa ett nytt prediktionspåstående.

Verifiering för v3.26.0:

- 264 / 264 pytest-tester passerar
- 5 nya Capture Quality Gate-tester ingår
- Python-kompilering verifierad
- centrala AST-kontroller verifierade
- ZIP-integritet verifieras före release
- Streamlit runtime/UI har inte visuellt verifierats i deploymiljö


## v3.27.0 – Snapshot Timing & Closing-Line Discipline

Historiken skiljer nu explicit på när en prognos sparades i förhållande till avspark. Syftet är att undvika en metodmiss där tidiga snapshots och snapshots nära avspark behandlas som om de vore samma typ av marknadsjämförelse.

Tidsklasser:

- inom 1 timme före avspark
- 1–3 timmar
- 3–12 timmar
- 12–24 timmar
- 24–72 timmar
- mer än 72 timmar
- efter avspark
- okänd timing.

Okänd timing räknas aldrig som nära-avspark-data. Observationer efter avspark är inte pre-match-observationer.

Benchmarkmotorn kan nu köras diagnostiskt med ett explicit maximalt antal timmar före avspark. UI visar därför en separat jämförelse för verifierade observationer som sparats högst tre timmar före avspark. Standardbenchmarken är oförändrad och använder fortsatt alla verifierade bookmakerobservationer.

Viktig metodregel: Streckverket använder inte termen **closing line** för dessa observationer. En snapshot nära avspark är inte samma sak som ett verifierat closing-odds. Closing-line-påståenden kräver en faktiskt tidsstämplad marknadspunkt som kan styrkas som closing-data.

Den aktuella kupongens Capture Quality Gate visar också närmaste kända avsparkstidpunkt i relation till sparögonblicket.


## v3.29.0 – Market Snapshot Timeline

- Separat, tidsstämplad marknadstidslinje för samma 13 matcher.
- Stabilt kupongfingeravtryck som inte påverkas av odds- eller streckförändringar.
- Marknadspunkter sparar bookmakerbas, källa, bookmakerantal och marknadens senaste uppdatering.
- Nästan identiska mätpunkter inom fem minuter dedupliceras för att undvika Streamlit-rerun-brus.
- Facitsparning lämnar automatiskt en marknadspunkt; ytterligare pre-match-punkter kan sparas manuellt.
- Historikvyn visar antal mättillfällen, täckning och förändring i marginalrensad 1/X/2-sannolikhet.
- Enskild matchs rörelse kan visas som tidsserie när minst två verifierade punkter finns.
- En punkt nära avspark kallas uttryckligen inte closing line utan verifierad closing-data.
- Demo och post-kickoff-capture blockeras från marknadstidslinjen.
- SQLite och PostgreSQL har separat market_points-tabell; facithistorikens befintliga payload-format lämnas intakt.
- Prognosmodell, systemoptimering och modellvikter är oförändrade.

Verifiering för releasen: 274/274 tester passerar. Streamlit UI/runtime är inte visuellt verifierad i deploymiljö.

## v3.37.0 – Expert Decision Summary

Expertläget börjar nu med en kort beslutsöversikt som återanvänder Streckverkets befintliga dataspärrar i stället för att skapa ett nytt expertbetyg. Översikten visar aktuell datastatus, historisk evidensstatus, att edge fortfarande inte är bevisad och en enda nästa bästa åtgärd.

Prioriteringsordningen är konservativ: demo/ofullständig kupong och saknad bookmakerbas går alltid före historiska signaler; därefter kommer aktuell readiness-diagnostik; först när den aktuella kupongens datagrind är klar får granskningsbara historiksegment bli nästa åtgärd. Evidence Dashboardens minimikrav och proveniensregler återanvänds oförändrade. Inga modellvikter eller systemstrategier ändras.


## v3.38.0 – Pre-Release Audit + Hidden Tab Execution Guard

Denna release gör ingen ändring i prognosmodellen eller systemstrategierna. Fokus är pre-release-härdning.

- Dolda Streamlit-flikar skyddas nu med `should_render_tab(...)`; CSS används endast för presentation.
- Normalläget kör därför inte längre innehållet i dolda expert-/specialistblock.
- Expertläge utan specialistverktyg kör endast core + primära expertflikar.
- Specialistläge återställer hela verktygslådan.
- Audit: `app.py` är fortfarande ca 2 400 rader och bör delas upp i kommande stabilitetsrelease.
- Audit: breda exception handlers finns kvar på flera ställen och bör granskas selektivt; inga stora felhanteringsrefaktorer gjordes här för att hålla release-risken låg.
- Streamlit runtime/UI är inte visuellt verifierad i deploymiljö.

Verifiering för v3.38.0: 317/317 pytest PASS, Python-kompilering OK, ZIP-integritet ska verifieras vid paketering.

## v3.45.0 – Model Change Registry

- Inför ett explicit register över dokumenterade modell-/metodförändringar per version.
- Registret visar föregående version, ändringstyp, berörda komponenter, sammanfattning, hypotes och om prognoslogiken faktiskt ändrades.
- v3.43–v3.45 registreras som metod/proveniensförbättringar utan prediktiv modelländring.
- Äldre eller okända versioner bakfylls aldrig genom gissning; de visas som **OKÄND**.
- Facit & lärande visar ändringsregistret bredvid versionsbenchmarken så framtida resultatskillnader kan kopplas till dokumenterade experiment.
- Prognosmodell och systemstrategier är oförändrade.

## v3.46.0 – Spelteori + Text-TV
- Nytt konservativt spelteorilager i Poolvärdesmotorn: publikträngsel, relativt värde och "motströms med stöd".
- Ren sällsynthet premieras inte; ett tecken måste ha sannolikhetsstöd från modellen.
- Funktionen är beslutsstöd och gör inget påstående om bevisad lönsam strategi.
- Visuell identitet omarbetad mot klassisk svensk Text-TV: svart botten, blå informationsfält, gul/cyan/grön signalfärg, monospace och kantiga block.
- Ingen ändring av prognosmodell eller systemstrategi.


## v3.49.0 – Decision Compression

- Sida 100 är nu en action-first beslutsruta: system/rader/pris, byggstruktur, readiness och upp till fyra befintliga nyckelåtgärder.
- Snabbvyn härleder endast från det redan optimerade systemet och befintliga klassificeringar. Den skapar inga nya tips.
- Normalvyn visar fördjupningen först efter ett aktivt val, vilket minskar informationsbelastningen.
- Direktknapp **Använd detta system** skickar samma optimerade system till Kupongverkstaden.
- Ingen ändring i `model_engine.py` eller `strategy_engine.py`.


## v3.51 – Budget Reallocation
- Text-TV sida 558 söker positiva omfördelningar av garderingar med exakt samma radantal.
- Användarlåsta matcher ändras aldrig.
- Funktionen är diagnostisk och ändrar inte modellmotorn eller ordinarie systemoptimering.


## v3.60.0 – Verified Pre-Kickoff Market Quality
- Ny modul `pre_kickoff_market_quality.py` jämför fryst/sparad bookmakerbild med senaste faktiskt verifierade marknadspunkt före avspark.
- Timing klassas konservativt som **MYCKET NÄRA** (≤60 min), **NÄRA** (1–3 h), **TIDIG** (>3 h) eller **OKÄND**. Ingen etikett kallas closing line.
- Ny Text-TV-sida **562 RÖRELSER** visar snapshot → sen verifierad förmarknad och största verkliga 1/X/2-rörelse.
- Riktning mot Streckverkets modell är endast diagnostik. Den används inte som modellvikt och är inte ett EV-/edge-påstående.
- Live-tidslinjens hjälpfunktion använder den tidigaste verifierade punkten som lokal baseline; historiska frysta prognoser kan anropa samma modul med den faktiska snapshotpunkten.
- `model_engine.py` och `strategy_engine.py` ändras inte i denna release.

## v3.61 – Prospective Late-Market Benchmark

Nya facit-snapshots länkas explicit till rätt marknadstidslinje via `market_timeline_key`. Historisk analys använder endast faktiskt senare verifierade bookmakerpunkter före avspark. Äldre snapshots bakåtkompletteras inte. Benchmarken visar om den senare marknaden rörde sig mot eller från den frysta modellen, segmenterat på initialt modell–marknad-gap, men påverkar inte prognos eller systemstrategi och innebär inget edge-/ROI-påstående.


## v3.62 – Automatic Late-Market Capture

Normalvyn sparar nu passivt verkliga verifierade bookmakerbilder före avspark när sidan körs. Oförändrade observationer dedupliceras, demodata och post-kickoff-data sparas inte. Funktionen finns för att mata v3.61:s prospektiva benchmark med riktig historik och ändrar varken prognosmotor eller systemstrategi.

## v3.63.0 – First-Time Player UX

Normalvyn har komprimerats för förstagångsspelare. Streckverkets rekommendation är standard, budget och systemförslag ligger i centrum, tre korta skäl förklarar beslutet och en enkel 13-matchersvy visar bara vad som ska spelas. Teknisk marknads-/API-diagnostik ligger bakom Fördjupad analys. Ingen prognos- eller strategimatematik ändrades.


## v3.64.0 – First-Run UX Wiring

v3.63:s förstagångsidé är nu faktiskt genomkopplad i `app.py`. Normalanvändaren får en primär knapp för aktuell Stryktipskupong, väljer maxbudget och får Streckverkets rekommendation som standard utan att se interna strateginamnen MAX 13/VÄRDE. CSV/demo ligger bakom ett sekundärt val och externa bookmaker-/API-inställningar visas endast i Expertläge. Huvudytan visar kostnad, spikar, garderingar, status, hela 13-matcherssystemet och högst tre korta varför-punkter. Den gamla tekniska Tipcentral-/Kupongöversikten körs bara i Expertläge. Ingen prognos- eller strategimatematik ändrades.
## v3.69.0 – Analysis Timing Guidance
Normalvyn visar nu både ett konkret readiness-besked och när användaren bör kontrollera kupongen igen. Tidsrådet baseras konservativt på tidigaste kända avspark och påstår inte att den tiden är Svenska Spels officiella spelstopp. v3.68:s handlingsbara readiness-logik är samtidigt faktiskt genomkopplad i `app.py`.


## v3.70.0 – One-Button Analysis Refresh
- Normalvyn har nu `Uppdatera analysen nu` som kör samma one-click-analys mot konfigurerade källor.
- Demo kan bytas till riktig aktuell kupong med samma knapp.
- En redan öppnad kupong byts aldrig mot en annan matchuppsättning under omanalys; färsk Svenska Spel-data används bara när samma 13 fixtures verifieras.
- Explicit refresh hämtar om kortlivade odds/fixture/skade/startelvslager men behåller stabil metadata-cache.
- Ingen prognos- eller strategimatematik är ändrad. Se `ANALYSIS_REFRESH_v3.70.md`.

- Korrigerar dessutom marknadsinsamlingens tidsproveniens: explicit observationstid bedöms mot kickoff i stället för dagens väggklocka.

## v3.80 – Experiment Lifecycle & Candidate Registry

Explicit kandidatregister och livscykel för prospektiva shadow-experiment. Förkastade kandidater stoppas från nya snapshots och kandidater som klarar governance-grinden pausas inför separat manuell granskning. Ingen automatisk produktionseffekt.

## v3.81 – Experiment Cohorts & Robustness
Prospektiva shadow-resultat segmenteras i fasta kohorter efter modellens förstaval (1/X/2), modellsäkerhet och modell–marknad-gap. Segment kräver minst 30 matcher över 5 kuponger innan de får bedömas. Diagnostiken ändrar inte produktion, kandidatparametrar eller systemstrategi.

## v3.84.0 – Spike Failure Lab

Prospektivt spiklabb som utvärderar de tecken systemet faktiskt frös som spikar före match. Det mäter träff mot fryst sannolikhet, kalibreringsgap per sannolikhetsintervall, samma-tecken-jämförelse mot bookmakerankaret och om missade spikar avvek från modellens eget förstaval. Minst 100 spikar över 20 kuponger krävs för övergripande slutsats; varje intervall kräver minst 20 spikar över 5 kuponger. Ingen automatisk spiktröskel, modellvikt eller systemregel ändras.


## v3.87 – System Decision Attribution

Hierarkisk attribution av prospektiva spik-, gardering- och systemstrukturdiagnoser. Överlappande P(13)-effekter dubbelräknas inte och ingen motor ändras automatiskt. Se `SYSTEM_DECISION_ATTRIBUTION_v3.87.md`.
