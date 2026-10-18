# Mexica astronomical tradition — research dossier

**People:** historical Mexica (Tenochca and related Nahua
informants in sixteenth-century sources).  
**Not merged with:** Maya, Mixtec, modern Nahua living practice,
or generic “Aztec mythology” web pages.

Stellarium’s `aztec` pack is a useful name index but is **not**
the primary source. It mixes Sahagún *Primeros Memoriales* with
weaker web pages and incorrectly illustrates the scorpion figure
from the **Maya** Paris Codex. Colotl Ixayac is **not** implemented
from that pack.

## Stronger identifications

### Tianquiztli / Pleiades + New Fire timing — READY

Sahagún *Primeros Memoriales* draws a compact many-star figure
labeled Tianquiztli (“marketplace”). Tezozomoc (1598) equates
Tianquiztli with *las Cabrillas* (Pleiades). Aveni and later
commentators accept the Pleiades identification. The same
cluster is the midnight-culmination check for the 52-year
New Fire / *xiuhmolpilli* ceremony on Huixachtécatl (Cerro de
la Estrella), described by Sahagún and discussed by Broda,
INAH, and Pérez Negrete (FAMSI).

This card is **historical calendrical astronomy**, not a living
Nahua teaching and not a generic Aztec myth page.

Sources:

- Sahagún, *Primeros Memoriales* and Florentine Codex Book VII
  (UNAM *Estudios de Cultura Náhuatl* paleography of Book VII
  ch. 3–6):
  https://nahuatl.historicas.unam.mx/index.php/ecn/article/download/77903/68956/228837
- Tezozomoc 1598, cited in UNAM *Gran Diccionario Náhuatl*
  (Tianquiztli = las Cabrillas; Mamalhuaztli also listed).
  https://gdn.iib.unam.mx/diccionario/mamalhuaztli/175024
- INAH *Arqueología Mexicana* / Jiménez on the New Fire temple
  at Huixachtécatl.
  https://www.revistas.inah.gob.mx/index.php/arqueologia/article/download/6392/7233/12653
- Miguel Pérez Negrete, “The Temple of the New Fire at the
  Huixachtécatl,” FAMSI.
  https://www.famsi.org/reports/01082/01082PerezNegrete01.pdf
- Johanna Broda, “La fiesta Azteca del fuego nuevo y el culto
  de las Pléyades” (1982) — cited, not copied.

### Templo Mayor solar / horizon alignments — READY

Šprajc (2000) measured Templo Mayor orientations against solar
horizon dates. A 2022 *PNAS* paper (Morehart / Hill / others)
reconstructs Basin of Mexico sunrise observatories and mountain
alignments, including Mount Tlaloc from Tenochtitlan near the
equinox / Tlaloc feast season. This is archaeoastronomy plus
ethnohistoric calendar, **not** a constellation myth.

Sources:

- Ivan Šprajc, “Astronomical alignments at the Templo Mayor of
  Tenochtitlan,” *Archaeoastronomy* 25 (2000).
- Morehart et al., *PNAS* 119 (2022):
  https://www.pnas.org/doi/10.1073/pnas.2215615119
- Aveni, Calnek, Hartung, “Myth, Environment, and the Orientation
  of the Templo Mayor,” *American Antiquity* (related discussion).

## Identifications with conflict — not implemented

| Name | Proposed IAU overlap | Problem | Status |
|---|---|---|---|
| Mamalhuaztli (fire-drill sticks) | Orion’s Belt / sword; or Hyades; or Castor & Pollux | Sahagún “Mastelejos,” Molina “Astillejos,” Tezozomoc “llaves de San Pedro” disagree | RESEARCH_MORE |
| Xonecuilli | Ursa Minor **or** Southern Cross | Stellarium and colonial sources disagree | RESEARCH_MORE |
| Citlaltlachtli | Gemini / ballcourt | Thin public mapping | RESEARCH_MORE |
| Colotl Ixayac / Citlalcolotl | Scorpius | Stellarium uses Maya Paris Codex art | DEFER |

## Modern Nahua

No modern Nahua-community educational pack was used. Historical
Mexica sources are labeled as such.

## Three Sisters

No Mexica source reviewed uses “Three Sisters.” Orion’s Belt as
English “Three Sisters” is not applied. Agricultural Three
Sisters is irrelevant here.

## Implementation

READY:

1. `mexica_tianquiztli`
2. `mexica_templo_mayor_solar`

## Deepening pass

Sahagún records a Templo Mayor precinct temple, Ilhuicatitlan,
whose priest watched Venus’s first morning appearance (heliacal
rise). Anales de Cuauhtitlán (UNAM) connects Quetzalcoatl /
Tlahuizcalpantecuhtli with the morning star. These are historical
Mexica/Nahua texts.

**Not promoted:** mixing Teotihuacan Venus observation projects
or Maya Venus tables with Mexica sources. A dedicated Venus card
stays **RESEARCH_MORE**.

Mount Tlaloc / Templo Mayor sunrise remains the implemented
solar-horizon card. Calendar-drift / observational-correction
claims were not added without a single clean public source.
