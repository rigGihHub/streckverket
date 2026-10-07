from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

UNKNOWN_VERSION = "OKÄND VERSION"


@dataclass(frozen=True)
class ModelChange:
    version: str
    parent_version: str | None
    change_type: str
    components: tuple[str, ...]
    summary: str
    hypothesis: str
    predictive_change: bool


# Deliberately explicit. Never infer historical model changes from release numbers.
_REGISTRY: dict[str, ModelChange] = {
    "3.43.0": ModelChange(
        version="3.43.0",
        parent_version="3.42.0",
        change_type="VALIDERING",
        components=("historik", "benchmark", "proveniens"),
        summary="Skärpte historisk validering med krav på separata kuponger och började versionsmärka nya facit-snapshots.",
        hypothesis="Metodförbättring för säkrare slutsatser; ingen ändring av prognossannolikheter.",
        predictive_change=False,
    ),
    "3.44.0": ModelChange(
        version="3.44.0",
        parent_version="3.43.0",
        change_type="VALIDERING",
        components=("versionsbenchmark", "historik"),
        summary="Delade benchmarkhistoriken per modellversion och spärrade jämförelser med för få separata kuponger.",
        hypothesis="Metodförbättring för rättvisare versionsjämförelser; ingen ändring av prognossannolikheter.",
        predictive_change=False,
    ),
    "3.45.0": ModelChange(
        version="3.45.0",
        parent_version="3.44.0",
        change_type="PROVENIENS",
        components=("modellregister", "versionsbenchmark"),
        summary="Införde ett explicit register över modell-/metodförändringar så framtida resultat kan kopplas till dokumenterade ändringar.",
        hypothesis="Spårbarhetsförbättring; ingen ändring av prognossannolikheter eller systemstrategi.",
        predictive_change=False,
    ),
    "3.46.0": ModelChange(
        version="3.46.0",
        parent_version="3.45.0",
        change_type="BESLUTSSTÖD/UI",
        components=("spelteori", "poolvärde", "text-tv-ui"),
        summary="Införde ett konservativt spelteorilager för publikträngsel/relativt värde samt Text-TV-inspirerad visuell identitet.",
        hypothesis="Bättre beslutspresentation och poolstrategi; ingen ändring av prognossannolikheter eller systemstrategi.",
        predictive_change=False,
    ),
    "3.47.0": ModelChange(
        version="3.47.0",
        parent_version="3.46.0",
        change_type="UI",
        components=("text-tv-ui", "normalvy"),
        summary="Införde Text-TV sida 551 för system och sida 552 för korta datadrivna matchråd.",
        hypothesis="Snabbare läsbarhet i normalflödet; ingen ändring av prognossannolikheter eller systemstrategi.",
        predictive_change=False,
    ),
    "3.48.0": ModelChange(
        version="3.48.0",
        parent_version="3.47.0",
        change_type="UI",
        components=("text-tv-navigation", "normalvy", "datastatus"),
        summary="Byggde sammanhängande Text-TV-sidor 100 och 551–556 för system, matchråd, spikar, fällor, skrällar och datastatus.",
        hypothesis="Kortare väg från analys till beslut utan nya prognosregler eller systemstrategier.",
        predictive_change=False,
    ),
    "3.49.0": ModelChange(
        version="3.49.0",
        parent_version="3.48.0",
        change_type="UI",
        components=("decision-compression", "text-tv-ui", "normalvy"),
        summary="Komprimerade normalvyn till sida 100 med system, readiness och befintliga nyckelåtgärder före fördjupningen.",
        hypothesis="Färre beslutsskikt och snabbare väg till ett begripligt system utan nya prognos- eller strategiregler.",
        predictive_change=False,
    ),
    "3.50.0": ModelChange(
        version="3.50.0",
        parent_version="3.49.0",
        change_type="BESLUTSSTÖD",
        components=("guarderingseffektivitet", "budgetdiagnostik", "text-tv-ui"),
        summary="Införde lokal marginalnytta för möjliga extra garderingar: täckningsökning, extra rader och kostnad per alternativ.",
        hypothesis="Bättre förståelse för var en gardering matematiskt ger mest modell-täckning per extra rad, utan ändring av prognossannolikheter eller ordinarie systemoptimering.",
        predictive_change=False,
    ),
    "3.51.0": ModelChange(
        version="3.51.0",
        parent_version="3.50.0",
        change_type="BESLUTSSTÖD",
        components=("budgetomfördelning", "garderingar", "text-tv-ui"),
        summary="Införde diagnostik som flyttar garderingsutrymme mellan matcher med exakt samma radantal och bara visar positiva täckningsförbättringar.",
        hypothesis="Bättre användning av en given radbudget utan högre kostnad; ingen ändring av prognossannolikheter eller ordinarie systemoptimering.",
        predictive_change=False,
    ),
    "3.52.0": ModelChange(
        version="3.52.0",
        parent_version="3.51.0",
        change_type="VALIDERING/BESLUTSSTÖD",
        components=("swap-backtest", "facit", "proveniens"),
        summary="Började spara de faktiska budgetomfördelningsförslag som visades före spelstopp och utvärdera dem först när komplett facit finns.",
        hypothesis="Prospektiv validering av omfördelningsdiagnostiken utan efterhandsrekonstruktion, ROI-antaganden eller ändring av prognosmotorn.",
        predictive_change=False,
    ),
    "3.53.0": ModelChange(
        version="3.53.0",
        parent_version="3.52.0",
        change_type="VALIDERING/BESLUTSSTÖD",
        components=("counterfactual-system-lab", "facit", "systemstrategi-proveniens"),
        summary="Fryser flera verkliga systemalternativ före spelstopp och jämför deras faktiska utfallstäckning på samma kupong och budget efter facit.",
        hypothesis="Prospektiv jämförelse av systembyggnadsstrategier utan efterhandskonstruktion, ROI-antaganden eller ändring av prognosmotorn.",
        predictive_change=False,
    ),
    "3.54.0": ModelChange(
        version="3.54.0",
        parent_version="3.53.0",
        change_type="VALIDERING/BESLUTSSTÖD",
        components=("strategy-league-table", "paired-comparison", "strategy-alias-provenance"),
        summary="Jämför systemstrategier parvis endast på kuponger där båda alternativen frystes före spelstopp och bevarar alias när flera strategier gav exakt samma system.",
        hypothesis="Rättvisare prospektiv strategiutvärdering genom matchade kuponger; ingen ROI-slutsats och ingen ändring av prognos- eller strategimotor.",
        predictive_change=False,
    ),
    "3.55.0": ModelChange(
        version="3.55.0",
        parent_version="3.54.0",
        change_type="VALIDERING/BESLUTSSTÖD",
        components=("strategy-robustness", "coupon-segmentation", "paired-comparison"),
        summary="Segmenterar frysta kuponger med förhandsbestämda mått för favoritbild, publikträngsel och modell–marknad-gap och granskar strategier parvis inom samma miljö.",
        hypothesis="Upptäcka om historiska strategimönster håller i kontrasterande kupongmiljöer utan att optimera segment efter facit eller ändra strategi automatiskt.",
        predictive_change=False,
    ),
    "3.56.0": ModelChange(
        version="3.56.0",
        parent_version="3.55.0",
        change_type="VALIDERING/BESLUTSSTÖD",
        components=("strategy-confidence", "multiple-testing", "paired-sign-test"),
        summary="Lägger ett parat kupongnivåtest och Holm-korrigering ovanpå segmenterad strategijämförelse för att minska risken för falska fynd vid många samtidiga tester.",
        hypothesis="Färre slumpmässiga strategisignaler när många kupongmiljöer granskas; ingen automatisk strategiändring, ROI-slutsats eller prognosförändring.",
        predictive_change=False,
    ),
    "3.57.0": ModelChange(
        version="3.57.0",
        parent_version="3.56.0",
        change_type="VALIDERING/BESLUTSSTÖD",
        components=("walk-forward-validation", "chronology", "paired-strategy-testing"),
        summary="Inför expanderande tidsordnad strategiutvärdering där äldre gemensamma kuponger väljer strategi och nästa senare kupongblock testar det frysta valet.",
        hypothesis="Minska återanvändning av samma historik för både strategival och utvärdering; ingen automatisk strategiändring, ROI-slutsats eller prognosförändring.",
        predictive_change=False,
    ),

    "3.58.0": ModelChange(
        version="3.58.0", parent_version="3.57.0",
        change_type="DATA/BESLUTSSTÖD",
        components=("market-intelligence", "bookmaker-consensus", "text-tv-560-566"),
        summary="Bevarar bookmaker-spridning, outliers och konsensusmetod från oddsflödet och visar marknadsintelligens separat från prognosmotorn.",
        hypothesis="Bättre beslut genom att skilja marknadens samstämmighet från Streckverkets egen modellavvikelse; ingen automatisk prognosvikt eller strategiändring.",
        predictive_change=False,
    ),
    "3.59.0": ModelChange(
        version="3.59.0", parent_version="3.58.0",
        change_type="VALIDERING/BESLUTSSTÖD",
        components=("market-disagreement-validation", "prospective-market-context", "model-market-gap"),
        summary="Validerar prospektivt modellens resultat mot bookmakerbasen separat i hög, normal och oenig marknad och visar explorativt modellgap inom samma frysta miljöer.",
        hypothesis="Avgöra om modellavvikelser beter sig annorlunda när bookmakers är samstämmiga respektive oeniga utan att låta marknadskonfidens påverka prognosen före evidens.",
        predictive_change=False,
    ),
    "3.60.0": ModelChange(
        version="3.60.0", parent_version="3.59.0",
        change_type="DATA/VALIDERING/BESLUTSSTÖD",
        components=("pre-kickoff-market-quality", "market-timeline", "text-tv-562"),
        summary="Jämför en fryst bookmakerbild med den senaste faktiskt verifierade marknadspunkt som lagrats före avspark och redovisar rörelse, timing och eventuell riktning mot modellen.",
        hypothesis="Bättre marknadsdiagnostik genom att mäta vad som faktiskt hände efter snapshot utan att felaktigt kalla sena observationer closing line eller låta rörelsen ändra prognosen.",
        predictive_change=False,
    ),
    "3.61.0": ModelChange(
        version="3.61.0", parent_version="3.60.0",
        change_type="DATA/VALIDERING",
        components=("facit-market-link", "late-market-benchmark", "prospective-provenance"),
        summary="Länkar nya frysta facit-snapshots explicit till rätt marknadstidslinje och benchmarkar endast faktiskt senare verifierade bookmakerpunkter före avspark.",
        hypothesis="Göra late-market-diagnostiken prospektivt utvärderingsbar över många kuponger utan historisk backfill, hindsight eller ändring av prognos-/strategimotor.",
        predictive_change=False,
    ),

    "3.62.0": ModelChange(
        version="3.62.0", parent_version="3.61.0",
        change_type="DATA/INSAMLING",
        components=("automatic-market-capture", "market-timeline", "prospective-late-market-data"),
        summary="Sparar automatiskt verkliga verifierade bookmakerbilder före avspark när normalvyn används, med befintlig deduplicering och utan att ändra prognosen.",
        hypothesis="Öka mängden prospektiv late-market-historik utan att kräva att vanliga användare manuellt driver ett expertflöde.",
        predictive_change=False,
    ),

    "3.63.0": ModelChange(
        version="3.63.0", parent_version="3.62.0",
        change_type="UX/BESLUTSSTÖD",
        components=("first-time-player-ux", "decision-page", "beginner-language"),
        summary="Komprimerar normalvyn för förstagångsspelare: standardrekommendation, enklare strategival, tre korta skäl, enkel 13-matchersvy och teknisk diagnostik bakom fördjupning.",
        hypothesis="Minska kognitiv belastning och göra vägen från budget till färdigt system tydligare utan att ändra prognos- eller strategimotorernas matematik.",
        predictive_change=False,
    ),
    "3.64.0": ModelChange(
        version="3.64.0", parent_version="3.63.0",
        change_type="UX/BESLUTSSTÖD",
        components=("app-wiring", "first-run-flow", "beginner-language", "expert-progressive-disclosure"),
        summary="Kopplar faktiskt in förstagångsflödet i app.py: aktuell kupong som primär handling, rekommenderad strategi som standard, enkel systemsammanfattning och tekniska odds-/diagnostikverktyg endast i expertläge.",
        hypothesis="Minska första-gångsfriktion genom att låta normalanvändaren gå direkt från kupong och budget till systemförslag utan att exponeras för interna strateginamn eller API-konfiguration.",
        predictive_change=False,
    ),
    "3.65.0": ModelChange(
        version="3.65.0", parent_version="3.64.0",
        change_type="UX/PRESTANDA",
        components=("single-screen-novice-flow", "navigation-compression", "progressive-disclosure", "automatic-market-capture"),
        summary="Tar bort den dubbla tabbnavigationen ur normalvyn och gör kupong, budget, system och kort förklaring till ett sammanhängande enskärmsflöde. Detaljflikar finns kvar i Expertläge och automatisk pre-kickoff-marknadsinsamling körs oberoende av tabs.",
        hypothesis="Minska kognitiv belastning och onödig Streamlit-rendering för nya användare utan att tappa expertfunktioner eller prospektiv marknadshistorik.",
        predictive_change=False,
    ),
    "3.66.0": ModelChange(
        version="3.66.0", parent_version="3.65.0",
        change_type="UX/BESLUTSSTÖD",
        components=("novice-system-board", "13-match-display", "mobile-readability", "beginner-language"),
        summary="Ersätter normalvyns tabell med en direkt 1/X/2-tavla för alla 13 matcher. Valda tecken markeras visuellt och varje rad etiketteras SPIK, HALV eller HEL; expertvyn och systemmatematiken lämnas oförändrade.",
        hypothesis="Göra det snabbare och mindre felkänsligt för en oerfaren användare att läsa av och föra över Streckverkets systemförslag till spelkupongen.",
        predictive_change=False,
    ),
    "3.67.0": ModelChange(
        version="3.67.0", parent_version="3.66.0",
        change_type="UX/BESLUTSSTÖD",
        components=("beginner-match-explanations", "novice-system-board", "progressive-disclosure"),
        summary="Lägger till korta, datadrivna förklaringar per match i normalvyn så att en ny spelare kan förstå varför systemet spikar, halv- eller helgarderar utan att öppna Expertläge.",
        hypothesis="Öka begripligheten i systemförslaget utan att lägga till nya modellregler, efterhandsförklaringar eller ändra systemmatematiken.",
        predictive_change=False,
    ),
    "3.68.0": ModelChange(
        version="3.68.0", parent_version="3.67.0",
        change_type="UX/BESLUTSSTÖD",
        components=("actionable-readiness", "novice-status", "progressive-disclosure"),
        summary="Översätter REDO/VÄNTA och befintliga datakvalitetsblockerare till ett konkret nybörjarbesked med exakt nästa steg. Datakvalitetspoängen flyttas från huvudbudskapet till en sekundär förklaring.",
        hypothesis="Minska osäkerheten efter analys genom att svara på vad användaren ska göra nu, utan att ändra readiness-regler, prognoser eller systemval.",
        predictive_change=False,
    ),

    "3.69.0": ModelChange(
        version="3.69.0", parent_version="3.68.0",
        change_type="UX/BESLUTSSTÖD",
        components=("analysis-timing", "actionable-readiness-wiring", "novice-status"),
        summary="Kopplar v3.68:s konkreta readiness-besked till den faktiska normalvyn och lägger till ett konservativt tidsråd för när kupongen bör analyseras igen, baserat på tidigaste kända avspark utan att kalla den officiellt spelstopp.",
        hypothesis="Minska risken att en oerfaren användare spelar på gammalt eller ofullständigt underlag genom att göra både status och nästa kontrolltid handlingsbara utan modellförändring.",
        predictive_change=False,
    ),

    "3.70.0": ModelChange(
        version="3.70.0", parent_version="3.69.0",
        change_type="UX/DATAUPPDATERING",
        components=("one-button-refresh", "coupon-identity-guard", "short-lived-cache-refresh", "novice-flow"),
        summary="Lägger till en enda uppdateringsknapp i normalvyn som kör om samma verifierade one-click-analys, skyddar mot att byta matchuppsättning och hämtar om kortlivade odds-, fixture-, skade- och startelvslager.",
        hypothesis="Göra det enkelt för en oerfaren användare att följa Streckverkets tids-/readinessråd utan att behöva förstå datakällor, cache eller Expertläge, samtidigt som kupongidentiteten förblir säker.",
        predictive_change=False,
    ),

    "3.71.0": ModelChange(
        version="3.71.0", parent_version="3.70.0",
        change_type="UX/FÖRÄNDRINGSRAPPORT",
        components=("analysis-change-report", "system-diff", "odds-diff", "lineup-readiness-diff"),
        summary="Visar efter en manuell omanalys vad som faktiskt ändrades sedan föregående analys: systemtecken, odds, startelvsunderlag och spelklarhetsstatus, utan att ändra modell eller strategi.",
        hypothesis="Göra omanalysen begriplig och värdefull för en oerfaren användare genom att skilja på verkliga förändringar och en uppdatering som lämnar systemet oförändrat.",
        predictive_change=False,
    ),

    "3.72.0": ModelChange(
        version="3.72.0", parent_version="3.71.0",
        change_type="UX/FÖRKLARBARHET",
        components=("analysis-change-reasons", "market-diff", "public-diff", "model-diff", "budget-reallocation-explanation"),
        summary="Förklarar systemändringar med verifierbara samtidiga skillnader i odds, streck, modell och lagunderlag. Om lokal förklaring saknas redovisas global budgetomfördelning eller att orsaken inte kan fastställas säkert.",
        hypothesis="Göra systemförändringar begripliga utan att tillskriva en enskild datakälla falsk kausalitet eller ändra prognos-/strategimotorerna.",
        predictive_change=False,
    ),

    "3.73.0": ModelChange(
        version="3.73.0", parent_version="3.72.0",
        change_type="UX/BESLUTSKOMPRIMERING",
        components=("key-coupon-decisions", "key-spike", "key-guard", "public-trap"),
        summary="Lyfter högst tre nyckelbeslut i normalvyn: starkaste systemspiken, viktigaste garderingen och en tydligt överstreckad folkfavorit när sådan finns, helt baserat på redan beräknade modell-/streckdata.",
        hypothesis="Hjälpa användaren förstå vilka matcher som bär mest beslutstyngd utan att lägga till nya signaler eller ändra prognos-/strategimotorerna.",
        predictive_change=False,
    ),

    "3.74.0": ModelChange(
        version="3.74.0", parent_version="3.73.0",
        change_type="VALIDERING/13-RÄTT",
        components=("13-right-performance-lab", "spike-miss-diagnostics", "guard-miss-diagnostics", "allocation-miss-diagnostics", "coupon-level-calibration"),
        summary="Mäter prospektivt varför sparade system missar 13 rätt och skiljer spik-/halvgarderingsmissar från fall där modellens förstaval var rätt men systemet ändå lämnade utfallet utanför.",
        hypothesis="Identifiera om nästa förbättring mot 13 rätt bör riktas mot prognoser, spikdisciplin eller system-/budgetallokering innan någon motor ändras.",
        predictive_change=False,
    ),

    "3.75.0": ModelChange(
        version="3.75.0", parent_version="3.74.0",
        change_type="VALIDERING/KALIBRERING",
        components=("probability-calibration", "spike-discipline-diagnostics", "model-vs-market-brier", "outcome-calibration"),
        summary="Mäter prospektivt kalibrering i frysta sannolikheter, särskilt 50–55 till 80+ procent och systemets faktiska spikar, samt jämför Brier/log loss mot verifierat bookmakerankare.",
        hypothesis="Avgöra om Streckverkets sannolikheter är tillräckligt kalibrerade för spikbeslut innan någon spiktröskel eller modellvikt ändras.",
        predictive_change=False,
    ),

    "3.76.0": ModelChange(
        version="3.76.0", parent_version="3.75.0",
        change_type="VALIDERING/SIGNALABLATION",
        components=("paired-model-market-validation", "divergence-buckets", "leave-one-signal-out", "prospective-factor-diagnostics"),
        summary="Jämför Streckverkets frysta sannolikheter och verifierat bookmakerankare parvis på exakt samma färdiga matcher och lägger leave-one-signal-out-diagnostik ovanpå prospektivt frysta faktorsnapshots.",
        hypothesis="Avgöra om modelljusteringarna faktiskt förbättrar marknadsankaret och vilka verifierade signaler som har positivt eller negativt marginalbidrag innan någon vikt ändras.",
        predictive_change=False,
    ),

    "3.77.0": ModelChange(
        version="3.77.0", parent_version="3.76.0",
        change_type="VALIDERING/BESLUTSGRIND",
        components=("market-anchor-decision-gate", "fixed-sample-guards", "divergence-risk", "experiment-candidate-gate"),
        summary="Sammanför parad modell-vs-marknad-validering, avvikelsesegment och signalablation i en konservativ beslutsgrind som avgör om ett separat prediktivt experiment kan motiveras.",
        hypothesis="Förhindra att små eller blandade historiska mönster leder till viktändringar och endast öppna för ett versionsregistrerat experiment när prospektiv evidens är tillräckligt samstämmig.",
        predictive_change=False,
    ),

    "3.78.0": ModelChange(
        version="3.78.0", parent_version="3.77.0",
        change_type="VALIDERING/PREDIKTIVT EXPERIMENT",
        components=("shadow-mode", "prospective-candidate-freeze", "baseline-candidate-market-comparison", "no-auto-promotion"),
        summary="Inför ett prospektivt shadow-läge där en förhandsregistrerad kandidatprognos fryses samtidigt som produktionsprognosen och senare jämförs mot både baseline och bookmakerankaret utan att påverka systemet.",
        hypothesis="Göra framtida prediktiva förändringar testbara på ny data före produktionssättning och förhindra historisk backfill eller automatisk promotion av en kandidat.",
        predictive_change=False,
    ),

    "3.79.0": ModelChange(
        version="3.79.0", parent_version="3.78.0",
        change_type="VALIDERING/GOVERNANCE",
        components=("shadow-governance", "promotion-gate", "coupon-breadth-check", "concentration-guard"),
        summary="Inför fasta governance-regler för att förkasta, fortsätta eller manuellt eskalera en prospektiv shadow-kandidat utan automatisk produktionssättning.",
        hypothesis="Minska risken att en kandidat promoveras på brus, enstaka kuponger eller för liten effekt genom att kräva större sample, bred förbättring och låg koncentration.",
        predictive_change=False,
    ),

    "3.80.0": ModelChange(
        version="3.80.0", parent_version="3.79.0",
        change_type="VALIDERING/EXPERIMENTLIVSCYKEL",
        components=("experiment-registry", "lifecycle-state", "snapshot-stop-gate", "candidate-provenance"),
        summary="Inför ett explicit register och deterministisk livscykel för shadow-experiment samt stoppar nya snapshots när en kandidat förkastats eller pausats för manuell granskning.",
        hypothesis="Förhindra sammanblandning, oavsiktlig återaktivering och fortsatt datainsamling efter ett avslutat shadow-beslut utan att ändra produktionens prognoser.",
        predictive_change=False,
    ),

    "3.81.0": ModelChange(
        version="3.81.0", parent_version="3.80.0",
        change_type="VALIDERING/ROBUSTHET",
        components=("shadow-cohorts", "robustness-diagnostics", "segment-stability"),
        summary="Segmenterar prospektiva shadow-resultat i fasta kohorter för att upptäcka kandidater vars totalresultat döljer svaghet i viktiga matchsegment.",
        hypothesis="En kandidat bör inte bedömas enbart på totalmått om förbättringen är instabil mellan utfall, sannolikhetsnivåer eller modell–marknad-gap.",
        predictive_change=False,
    ),

    "3.82.0": ModelChange(
        version="3.82.0", parent_version="3.81.0",
        change_type="DRIFT/DEPLOYMENT",
        components=("windows-launcher", "container-deployment", "persistent-history-config", "release-info"),
        summary="Gör appen startbar via Windows-dubbelklick och förbereder säker webbdeploy med explicit konfiguration för beständig prospektiv historik.",
        hypothesis="Minska driftfriktion utan att ändra prognos- eller strategimotorernas matematik.",
        predictive_change=False,
    ),

    "3.83.0": ModelChange(
        version="3.83.0", parent_version="3.82.0",
        change_type="VALIDERING/SYSTEM-P13",
        components=("frozen-system-p13-audit", "same-budget-headroom", "allocation-diagnostics", "no-hindsight-reconstruction"),
        summary="Granskar om före-match frysta systemalternativ inom samma budgetram hade högre modellbaserad P(13) än originalsystemet, utan att rekonstruera äldre kuponger efter facit.",
        hypothesis="Avgöra om system-/budgetallokeringen lämnar återkommande P(13)-potential på bordet innan strategimotorn ändras.",
        predictive_change=False,
    ),
    "3.84.0": ModelChange(
        version="3.84.0", parent_version="3.83.0",
        change_type="VALIDERING/DIAGNOSTIK",
        components=("spikdisciplin", "kalibrering", "facit"),
        summary="Inför prospektiv Spike Failure Lab som mäter träff, kalibrering och bookmakerjämförelse för faktiskt frysta spikar utan att ändra spiktröskel eller prognosmotor.",
        hypothesis="Skilja systematisk spiköverkonfidens och systemets spikval från normal slump i enskilda missar innan ett prediktivt experiment övervägs.",
        predictive_change=False,
    ),

    "3.85.0": ModelChange(
        version="3.85.0", parent_version="3.84.0",
        change_type="VALIDERING/SYSTEMALLOKERING",
        components=("guard-allocation-lab", "same-row-counterfactuals", "p13-headroom", "no-hindsight-reconstruction"),
        summary="Granskar om före-match frysta system med exakt samma radantal återkommande kunde flytta garderingar mellan matcher och höja modellbaserad P(13).",
        hypothesis="Avgöra om halv-/helgarderingar placeras ineffektivt utan att blanda ihop allokering med högre insats eller använda facit för att välja alternativ.",
        predictive_change=False,
    ),

    "3.86.0": ModelChange(
        version="3.86.0", parent_version="3.85.0",
        change_type="VALIDERING/COUNTERFACTUAL-OPTIMERING",
        components=("counterfactual-13-optimizer-audit", "same-row-structure", "p13-headroom", "no-hindsight-selection"),
        summary="Granskar om ett redan före-match fryst system med exakt samma radantal hade högre modellbaserad P(13) genom en annan kombination av spikar och garderingar.",
        hypothesis="Avgöra om systemstrukturen lämnar återkommande P(13)-headroom inom samma radbudget innan strategy_engine ändras.",
        predictive_change=False,
    ),

    "3.87.0": ModelChange(
        version="3.87.0", parent_version="3.86.0",
        change_type="VALIDERING/BESLUTSATTRIBUTION",
        components=("system-decision-attribution", "hierarchical-diagnostics", "no-double-counting", "experiment-priority"),
        summary="Sammanför spik-, gardering- och systemstrukturauditer hierarkiskt utan att summera överlappande P(13)-effekter och pekar ut nästa experimentområde när underlaget är moget.",
        hypothesis="Göra nästa strategi- eller kalibreringsexperiment mer träffsäkert genom att skilja direkt system-headroom från separat prediktiv spikevidens.",
        predictive_change=False,
    ),

    "3.88.0": ModelChange(
        version="3.88.0", parent_version="3.87.0",
        change_type="UX/NORMALFLÖDE",
        components=("novice-landing", "sidebar-simplification", "demo-safety", "information-hierarchy"),
        summary="Förenklar normalflödet så demo inte ser spelklar ut, minskar sidopanelens brus och visar systemförslaget före diagnostik och uppdateringsdetaljer.",
        hypothesis="Minska risken att normalanvändaren misstolkar testdata eller tappar huvuduppgiften utan att ändra prognos- eller strategilogik.",
        predictive_change=False,
    ),

    "3.89.0": ModelChange(
        version="3.89.0", parent_version="3.88.0",
        change_type="UX/STARTFLÖDE",
        components=("first-analysis", "csv-recovery", "loading-feedback", "demo-safety"),
        summary="Synlig första analys, laddningsindikator och CSV-reserv på startsidan. CSV kräver ett explicit öppningsklick och fel lämnar kupongen orörd. Misslyckad hämtning får inte göra testkupongen till verkligt underlag.",
        hypothesis="Ett fungerande startflöde utan omladdningsloopar eller testdata som uppfattas som riktiga matcher. Ingen prognos- eller strategiändring.",
        predictive_change=False,
    ),
    "3.89.1": ModelChange(
        version="3.89.1", parent_version="3.89.0",
        change_type="UI/BUDGET",
        components=("shared-budget", "system-summary", "decision-page"),
        summary="Samlar beloppsfälten i en gemensam budget så systemkostnad och systemflik uppdateras vid ändring i beslutsvyn eller sidopanelen. Budgeten bevaras mellan visningslägen.",
        hypothesis="Konsekvent systemförslag för valt maxbelopp utan ändring av prognos- eller optimeringslogik.",
        predictive_change=False,
    ),
}


def get_model_change(version: str) -> ModelChange | None:
    return _REGISTRY.get(str(version or "").strip())


def registered_changes() -> tuple[ModelChange, ...]:
    return tuple(_REGISTRY[v] for v in sorted(_REGISTRY))


def change_rows_for_versions(versions: Sequence[str]) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()
    for raw in versions:
        version = str(raw or "").strip() or UNKNOWN_VERSION
        if version in seen:
            continue
        seen.add(version)
        change = get_model_change(version)
        if change is None:
            rows.append({
                "Modellversion": version,
                "Föregående": "–",
                "Typ": "OKÄND",
                "Berör": "–",
                "Dokumenterad ändring": "Ändringspost saknas. Streckverket gissar inte vad som ändrades.",
                "Hypotes": "–",
                "Ändrade prognosen?": "OKÄNT",
            })
            continue
        rows.append({
            "Modellversion": change.version,
            "Föregående": change.parent_version or "–",
            "Typ": change.change_type,
            "Berör": ", ".join(change.components),
            "Dokumenterad ändring": change.summary,
            "Hypotes": change.hypothesis,
            "Ändrade prognosen?": "JA" if change.predictive_change else "NEJ",
        })
    return rows
