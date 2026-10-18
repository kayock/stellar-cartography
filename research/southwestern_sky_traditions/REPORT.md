# Southwestern sky traditions — research report

Date: 2026-10-10 (deepening pass)  
Scope: research first; implement only READY public cards. Archaeoastronomy Visual Mode uses only sourced claims.

## 1. Sources reviewed

Twenty-plus items were read or inspected, including:

- Diné-authored / Diné-approved education (Maryboy & Begay 2010;
  NASA–Navajo Nation *Story of the Stars*; STARLAB Navajo Skies;
  *Navajo Times* Diné College report)
- Stellarium `navajo` and `aztec` packs (secondary; not primary)
- Farrer 1987 Mescalero ceremonial star-clock paper
- Mescalero and Jicarilla tribal museum/heritage sites
- Museum of New Mexico Foundation *Makowa* announcement
- NPS “Archeoastronomy in Stone,” Chaco/Fajada brochures, Pueblo
  Bonito and Casa Rinconada pages
- Sofaer et al. 1979 *Science*; later Solstice Project papers
- Sahagún / UNAM Book VII; UNAM Gran Diccionario Náhuatl;
  INAH New Fire article; Pérez Negrete FAMSI; Šprajc 2000; PNAS 2022
- Hopi Cultural Preservation Office pointers, McCluskey 1990,
  HAO Hopi sun-watching page
- Mesa Verde Voices Zuni/Diné star-watching episode
- UNM-Taos Cielo Centro (STEM, not Taos Pueblo tradition)
- NPS Holly Petroglyph Panel / Holly Group (Hovenweep)
- NPS Mesa Verde Sun Temple place page; Reyman 1977 *Kiva* correction
- HAO Cliff Palace / Sun Temple education note
- Sahagún Book II Ilhuicatitlan / Venus heliacal-rise note; Anales de
  Cuauhtitlán morning-star passage (UNAM)
- A:shiwi A:wan Museum *Ulohnanne* exhibit; El Morro NPS Zuni
  constellation program announcement
- Jicarilla Cultural Arts & Heritage Center revisit; Great Sand Dunes
  “Jicarilla Apache Star Stories” video (not reusable text)
- STARLAB / NASA Diné education PDFs reconfirmed seasonal-only

Full rows: `source_matrix.json`.

## 2. Communities / traditions researched

Diné; Mescalero, Jicarilla, and other Apache peoples as
distinguished groups; Hopi; Zuni (A:shiwi); Acoma; Taos Pueblo
(insufficient); Ancestral Puebloan archaeological context;
historical Mexica. Maya and generic “Aztec mythology” pages were
not used as Mexica sources.

## 3. Candidate stories

| story_id | tradition | people | target | public | sources | Stellarium map | rec |
|---|---|---|---|---|---|---|---|
| dine_dilyehe | Diné | Diné | Pleiades | seasonal-only | A (Maryboy/Begay; NASA) | high | RESTRICTED |
| dine_atse_etsozi | Diné | Diné | Orion | seasonal-only | A | high | RESTRICTED |
| dine_nahookos | Diné | Diné | UMa/Cas/Polaris | seasonal-only | A | high | RESTRICTED |
| mescalero_star_clock | Mescalero Apache | Mescalero | UMa / Capella | ceremonial | B (Farrer) | medium | RESTRICTED |
| hopi_horizon_sun | Hopi | Hopi | Sun | ceremonial calendar | B | high (Sun) | RESEARCH_MORE |
| hopi_pleiades | Hopi | Hopi | Pleiades | unclear / secondary names | B/weak | high | DEFER |
| zuni_glittering_stars | Zuni | A:shiwi | general sky | prayer context | A-thin | low | RESEARCH_MORE |
| fajada_sun_dagger | Ancestral Puebloan | Chaco archaeological | Sun / solstice | public NPS | C | high (Sun) | READY |
| chaco_cardinal | Ancestral Puebloan | Chaco archaeological | Sun / Polaris as modern north ref | public | C | high | READY |
| casa_rinconada_solstice | Ancestral Puebloan | Chaco | Sun | contested reconstruction | C/D | medium | RESEARCH_MORE |
| penasco_blanco_1054 | Ancestral Puebloan | Chaco | Crab / Moon | “may depict” | C | high | RESEARCH_MORE |
| mexica_tianquiztli | Mexica historical | Mexica / Nahua informants | Pleiades | historical public texts | B | high | READY |
| mexica_templo_mayor_solar | Mexica historical | Mexica | Sun / horizon | public scholarship | C+B | high (Sun) | READY |
| mexica_mamalhuaztli | Mexica historical | Mexica | Orion? Hyades? Gemini? | public but conflicting IDs | B | low | RESEARCH_MORE |
| mexica_xonecuilli | Mexica historical | Mexica | UMi or Crux | conflicting | B | low | RESEARCH_MORE |
| mexica_colotlixayac | Mexica? | mixed | Scorpius | Stellarium uses Maya art | D | n/a | DEFER |
| holly_solstice_panel | Ancestral Puebloan | Hovenweep archaeological | Sun / summer solstice | public NPS | C | high (Sun) | READY |
| mesa_verde_sun_temple | Ancestral Puebloan | Mesa Verde archaeological | Sun | NPS “possible”; Fewkes wall claim disproved | C/D | medium | RESEARCH_MORE |
| mexica_venus_ilhuicatitlan | Mexica historical | Mexica | Venus | Sahagún temple note; omen texts | B | high (Venus) | RESEARCH_MORE |

## 4. READY stories (implemented)

1. `ancestral_puebloan_fajada_sun_dagger`
2. `ancestral_puebloan_chaco_cardinal`
3. `mexica_tianquiztli`
4. `mexica_templo_mayor_solar`
5. `ancestral_puebloan_holly_solstice_panel` (deepening pass)

## 5. RESEARCH_MORE

Hopi horizon calendar with community review; Zuni named
asterisms from A:shiwi A:wan; Casa Rinconada niche light;
Peñasco Blanco supernova; Mamalhuaztli and Xonecuilli
identifications; Jicarilla/Western Apache public education
if *Makowa* or tribal centers publish reusable text.
Mesa Verde Cliff Palace–Sun Temple winter sunset (NPS “possible”;
depends on reconstructed tower height). Mexica Venus / Ilhuicatitlan
heliacal-rise temple (Sahagún) until a tight historical card can
be written without mixing Teotihuacan or Maya Venus tables.

## 6. DEFERRED

Generic pan-Pueblo cards; Acoma; Taos Pueblo (Cielo Centro is
STEM); Stellarium-only Diné/Aztec reconstructions; Colotl
Ixayac from Maya Paris Codex; living Pueblo katsina/star-name
cards without community-authored public text.

## 7. RESTRICTED

All Diné constellation *stories* (seasonal protocol).  
Mescalero puberty-ceremonial star timing.  
Hopi material flagged as not-for-sharing in community talks.  
Creation-hogan / Black God ceremonial accounts.

## 8. Shared motifs (not common origin)

| motif_id | traditions that *could* map | status |
|---|---|---|
| pleiades_seasonal_marker | Mexica Tianquiztli (READY); Diné Dilyéhé (restricted, not shown); existing Māori Matariki; existing Arabian al-Thurayyā; modern IAU Taurus | `independent_similarity` |
| solar_horizon_or_solstice | Ancestral Puebloan Fajada/Chaco; Hopi sun-watching (not implemented); Mexica Templo Mayor | `independent_similarity` |
| three_star_line | English “Three Sisters” = Orion’s Belt (not Indigenous here); Mamalhuaztli disputed | `unknown` — not implemented |

No source reviewed documents a single ancient source for these
parallels. No `documented_exchange` is claimed.

## 9. Archaeological vs living-tradition

Ancestral Puebloan cards are `evidence_type=archaeological_inference`
and `living_tradition=false`.  
Mexica cards are historical/scholarly (`scholarly_ethnographic` or
mixed archaeoastronomy) and `living_tradition=false`.  
They are not presented as extinct folklore, nor as modern Nahua
or Pueblo oral tradition.

## 10. Terminology

Primary display: Ancestral Puebloan; Diné; specific Apache
nation; specific Pueblo; historical Mexica.  
Avoided: Native American mythology; Aztec mythology; Apache
as one sky; Pueblo as one sky.

## 11. Ancestral Puebloan / Anasazi

Display = Ancestral Puebloan.  
`search_aliases` include Anasazi.  
`terminology_note` explains the older documentary term.

## 12. Similarities not treated as common origin

Pleiades as a seasonal or ceremonial timing object appears in
several independent traditions already in Cartography. The new
Mexica card joins **Same sky — different stories** for M45 only
because the astronomical object is the same. Traditions remain
separate and independently sourced.

Archaeoastronomy cards may appear together as **similar
observational function** (solar-year markers). That label does
not imply a shared tradition.

## 13. Deepening pass — claim classification

| claim | class | production use |
|---|---|---|
| Fajada slabs + spirals + midday light (1979; NPS) | CONFIRMED / STRONG | visual primary |
| Fajada as solstice/equinox calendar (NPS “believed”) | PLAUSIBLE / SCHOLARLY INTERPRETATION | visual badge |
| Fajada lunar standstill | DISPUTED | research context only |
| Chaco near-cardinal walls | CONFIRMED / STRONG | visual primary |
| Chaco axes as solar-noon / equinox markers | PLAUSIBLE / SCHOLARLY INTERPRETATION | visual primary |
| Casa Rinconada niche light | DISPUTED | omitted from diagram |
| Holly boulder-gap solstice beam (NPS) | CONFIRMED / STRONG (observable); SCHOLARLY (intent) | READY card |
| Mesa Verde Sun Temple south-wall solstice (Fewkes) | DISPUTED (Reyman 1977) | not implemented |
| Mesa Verde winter sunset from Cliff Palace | PLAUSIBLE / SCHOLARLY INTERPRETATION | foundation only |
| Templo Mayor / Mount Tlaloc sunrise | PLAUSIBLE / SCHOLARLY INTERPRETATION | existing card |
| Mexica Venus as morning star / Tlahuizcalpantecuhtli | PLAUSIBLE in historical texts; mix-risk with Teotihuacan/Maya | RESEARCH_MORE |
