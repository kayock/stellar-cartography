#!/usr/bin/env python3
"""Append READY Southwestern / Mexica stories. Not imported by the app."""

from __future__ import annotations

import json
from pathlib import Path

REG = Path(__file__).resolve().parents[1] / "app" / "data" / "constellation_story_registry.json"

SUN = {
    "id": "sun",
    "name": "Sun",
    "search_name": "Sun",
    "kind": "sun",
    "aliases": ["sol"],
    "designations": ["Sol"],
    "notes": "Stellarium-verified focus target for solar / horizon cards.",
    "fov_deg": 8,
}

POLARIS = {
    "id": "polaris",
    "name": "Polaris",
    "search_name": "Polaris",
    "kind": "star",
    "aliases": ["north star", "alpha ursae minoris"],
    "designations": ["α UMi"],
    "notes": "Modern north celestial pole star used here as a tour reference for cardinal architecture, not as an Ancestral Puebloan constellation.",
    "fov_deg": 12,
}

PLEIADES = {
    "id": "pleiades",
    "name": "Tianquiztli / Pleiades",
    "search_name": "Pleiades",
    "kind": "cluster",
    "aliases": ["m45", "tianquiztli", "cabrillas"],
    "designations": ["M 45"],
    "notes": "Stellarium search target for the historical Mexica marketplace asterism.",
    "fov_deg": 4,
}

ALCYONE = {
    "id": "alcyone",
    "name": "Alcyone",
    "search_name": "Alcyone",
    "kind": "star",
    "aliases": ["eta tauri"],
    "designations": ["η Tau"],
    "notes": "Brightest star in the cluster; a Stellarium tour step, not a Nahuatl personal name.",
    "fov_deg": 3,
}

ANASAZI_NOTE = (
    "Older archaeological and documentary sources frequently use 'Anasazi'; "
    "Cartography uses 'Ancestral Puebloan' as the primary display term."
)

ENTRIES = [
    {
        "id": "ancestral_puebloan_fajada_sun_dagger",
        "story_kind": "cultural_sky_story",
        "culture_id": "ancestral_puebloan",
        "culture_name": "Ancestral Puebloan",
        "tradition_name": "Ancestral Puebloan archaeoastronomy (Chaco Canyon)",
        "story_type": "archaeoastronomy",
        "evidence_type": "archaeological_inference",
        "living_tradition": False,
        "public_story_status": "public",
        "source_region": "Chaco Canyon, northwestern New Mexico",
        "source_people": "Ancestral Puebloan builders of Chaco Canyon",
        "canonical_name": "Fajada Butte Sun Dagger",
        "native_name": None,
        "translated_name": "Fajada Butte solar dagger",
        "abbreviation": "",
        "aliases": ["sun dagger", "fajada butte", "chaco sun dagger"],
        "search_aliases": ["Anasazi", "Ancestral Pueblo", "Ancient Puebloan"],
        "terminology_note": ANASAZI_NOTE,
        "sky_culture": "ancestral_puebloan",
        "iau_overlap": [],
        "archaeological_context": "Three sandstone slabs on Fajada Butte channel midday sunlight onto spiral petroglyphs. Public access is closed.",
        "cultures": [
            {
                "id": "ancestral_puebloan",
                "name": "Ancestral Puebloan",
                "constellation_name": "Fajada Butte Sun Dagger",
                "mythology_summary": "Archaeological interpretations suggest the Fajada Butte slabs and spirals marked solstices and equinoxes with changing midday light. This is not presented as a surviving oral constellation story.",
                "artwork_ref": None,
            }
        ],
        "mythology_summary": "Archaeological interpretations suggest that three sandstone slabs on Fajada Butte, at Chaco Culture National Historical Park, once sent dagger-shaped midday sunlight across two spiral petroglyphs at the solstices and equinoxes. The National Park Service reports the site is no longer open; visitor erosion later shifted the slabs so the original centered summer pattern no longer occurs. This card does not claim to retell a living Pueblo oral story.",
        "science_summary": "The Sun's changing noon altitude through the year can produce a calendar of light and shadow. NASA or Chandra images of the Sun, if shown, are modern scientific views and are not Ancestral Puebloan sources.",
        "story_summary": "Public archaeoastronomy of the Fajada Butte solar marker.",
        "astronomy_context": "Solar declination / midday altitude; solstice and equinox.",
        "narration_lead": "This archaeological interpretation of Ancestral Puebloan observations suggests the Fajada Butte Sun Dagger marked the solar year with midday light on spiral petroglyphs.",
        "major_objects": [SUN],
        "notable_deep_sky_objects": [],
        "story_order": ["sun"],
        "cosmic_signal_tags": [],
        "spectrum_tags": [],
        "media_tags": ["sun"],
        "shared_motifs": [
            {
                "motif_id": "solar_horizon_or_solstice",
                "tradition_story_ids": [
                    "ancestral_puebloan_fajada_sun_dagger",
                    "ancestral_puebloan_holly_solstice_panel",
                    "mexica_templo_mayor_solar",
                ],
                "astronomical_region": "Sun / solstice-equinox",
                "similarity_description": "Independent public records of solar-year marking. Not evidence of a shared origin story.",
                "relationship_status": "independent_similarity",
                "source_support": "NPS archaeoastronomy page; Sofaer 1979 for Chaco. PNAS 2022 / Šprajc for Mexica — separate sources.",
            }
        ],
        "related_story_ids": ["ancestral_puebloan_chaco_cardinal", "ancestral_puebloan_holly_solstice_panel"],
        "source_notes": [
            "NPS: believed to have marked summer and winter solstices and equinoxes.",
            "Sofaer, Zinser, and Sinclair 1979 described the original midday dagger patterns.",
            "Lunar-standstill claims are not included here.",
            "Display term is Ancestral Puebloan; Anasazi is a search alias only.",
        ],
        "source_urls": [
            {
                "title": "Archeoastronomy in Stone",
                "institution": "U.S. National Park Service",
                "date": "2024-01-23",
                "url": "https://www.nps.gov/articles/000/archeoastronomy-in-stone.htm",
                "supports": "Public NPS framing of the Fajada Butte Sun Dagger as a solstice/equinox marker; site closed; Ancestral Pueblo terminology.",
            },
            {
                "title": "A Unique Solar Marking Construct",
                "institution": "Science / Solstice Project",
                "date": "1979",
                "url": "https://solsticeproject.org/wp-content/uploads/2021/12/19-uniquesolar2028197929.pdf",
                "supports": "Original published description of the slab-and-spiral midday solar construct.",
            },
        ],
        "source_quality": "scholarly",
        "cultural_note": "Archaeological inference about seasonal observation, not mythology.",
        "enabled": True,
    },
    {
        "id": "ancestral_puebloan_chaco_cardinal",
        "story_kind": "cultural_sky_story",
        "culture_id": "ancestral_puebloan",
        "culture_name": "Ancestral Puebloan",
        "tradition_name": "Ancestral Puebloan archaeoastronomy (Chaco Canyon)",
        "story_type": "solar_lunar_alignment",
        "evidence_type": "archaeological_inference",
        "living_tradition": False,
        "public_story_status": "public",
        "source_region": "Chaco Canyon, northwestern New Mexico",
        "source_people": "Ancestral Puebloan builders of Chaco Canyon",
        "canonical_name": "Chaco Cardinal Architecture",
        "native_name": None,
        "translated_name": "Chaco north–south and east–west alignments",
        "abbreviation": "",
        "aliases": ["pueblo bonito alignment", "chaco cardinal", "casa rinconada"],
        "search_aliases": ["Anasazi", "Ancestral Pueblo", "Ancient Puebloan"],
        "terminology_note": ANASAZI_NOTE,
        "sky_culture": "ancestral_puebloan",
        "iau_overlap": [],
        "archaeological_context": "Great-house and great-kiva axes at Chaco are documented near true cardinal directions. A specific Casa Rinconada summer-solstice niche light is contested after 1930s reconstruction and is not claimed here.",
        "cultures": [
            {
                "id": "ancestral_puebloan",
                "name": "Ancestral Puebloan",
                "constellation_name": "Chaco Cardinal Architecture",
                "mythology_summary": "Archaeological interpretations suggest several Chaco constructions were laid out on near-cardinal axes. This is architecture, not a named star figure.",
                "artwork_ref": None,
            }
        ],
        "mythology_summary": "Archaeological interpretations suggest that Pueblo Bonito and other Chaco Canyon constructions include walls and axes within a fraction of a degree of true north–south and east–west. Knowledge of those axes can mark solar noon and the equinoxes. Polaris is shown in the tour only as a modern north-sky reference. It is not presented as an Ancestral Puebloan constellation. The popular Casa Rinconada niche-light effect is omitted because reconstruction makes the original opening uncertain.",
        "science_summary": "A building aligned to true north lets a shadow cross a north–south line at local solar noon. NASA imagery, if shown, is a modern scientific view of the Sun or north sky, not a Chaco source.",
        "story_summary": "Cardinal architectural astronomy at Chaco.",
        "astronomy_context": "Cardinal directions; solar noon; equinox east–west.",
        "narration_lead": "This archaeological interpretation of Ancestral Puebloan observations suggests major Chaco buildings were aligned close to the cardinal directions.",
        "major_objects": [SUN, POLARIS],
        "notable_deep_sky_objects": [],
        "story_order": ["sun", "polaris"],
        "cosmic_signal_tags": [],
        "spectrum_tags": [],
        "media_tags": ["sun"],
        "shared_motifs": [
            {
                "motif_id": "solar_horizon_or_solstice",
                "tradition_story_ids": [
                    "ancestral_puebloan_chaco_cardinal",
                    "ancestral_puebloan_holly_solstice_panel",
                    "mexica_templo_mayor_solar",
                ],
                "astronomical_region": "Sun / cardinal and horizon geometry",
                "similarity_description": "Independent architectural uses of the solar year. Not a shared myth.",
                "relationship_status": "independent_similarity",
                "source_support": "NPS / Solstice Project for Chaco; Šprajc and PNAS 2022 for Tenochtitlan.",
            }
        ],
        "related_story_ids": ["ancestral_puebloan_fajada_sun_dagger", "ancestral_puebloan_holly_solstice_panel"],
        "source_notes": [
            "NPS identifies Pueblo Bonito as an Ancestral Puebloan great house (about AD 850–1150).",
            "Survey literature reports cardinal axes at Pueblo Bonito and related constructions.",
            "Casa Rinconada summer-solstice niche light is not treated as settled.",
        ],
        "source_urls": [
            {
                "title": "Pueblo Bonito",
                "institution": "U.S. National Park Service, Chaco Culture National Historical Park",
                "date": "2017-12-18",
                "url": "https://www.nps.gov/chcu/planyourvisit/pueblo-bonito.htm",
                "supports": "Ancestral Puebloan identification and public site context for Pueblo Bonito.",
            },
            {
                "title": "Archeoastronomy in Stone",
                "institution": "U.S. National Park Service",
                "date": "2024-01-23",
                "url": "https://www.nps.gov/articles/000/archeoastronomy-in-stone.htm",
                "supports": "NPS statement that Chaco complexes were oriented to mark astronomical time.",
            },
        ],
        "source_quality": "scholarly",
        "cultural_note": "Architectural astronomy. Not a constellation myth.",
        "enabled": True,
    },
    {
        "id": "mexica_tianquiztli",
        "story_kind": "cultural_sky_story",
        "culture_id": "mexica",
        "culture_name": "Mexica (historical)",
        "tradition_name": "historical Mexica calendrical astronomy (Sahagún / colonial Nahuatl sources)",
        "story_type": "calendrical_astronomy",
        "evidence_type": "scholarly_ethnographic",
        "living_tradition": False,
        "public_story_status": "public",
        "source_region": "Basin of Mexico / Tenochtitlan",
        "source_people": "historical Mexica / Nahua informants recorded in sixteenth-century sources",
        "canonical_name": "Tianquiztli",
        "native_name": "Tianquiztli",
        "translated_name": "the Marketplace (Pleiades)",
        "abbreviation": "Tau",
        "aliases": ["tianquiztli", "tianguis", "mastelejos", "cabrillas", "pleiades"],
        "search_aliases": ["Aztec Pleiades", "Tianquiztli"],
        "sky_culture": "mexica",
        "stellarium_culture_ids": ["aztec"],
        "iau_overlap": ["Tau"],
        "cultures": [
            {
                "id": "mexica",
                "name": "Mexica (historical)",
                "constellation_name": "Tianquiztli",
                "mythology_summary": "In the Mexica historical sources represented here, Tianquiztli is the Pleiades, used in calendrical timing including the 52-year New Fire / xiuhmolpilli watch.",
                "artwork_ref": None,
            }
        ],
        "mythology_summary": "In the Mexica historical sources represented here, Tianquiztli — the marketplace — is identified with the Pleiades (Spanish colonial 'Cabrillas' / 'Mastelejos'). Sahagún's Primeros Memoriales draws a compact many-star figure. Related colonial and INAH discussions connect the midnight culmination of this group to the New Fire ceremony that bound the 52-year cycle (xiuhmolpilli) at Huixachtécatl, the Hill of the Star. This is historical calendrical astronomy, not a modern Nahua teaching and not a collapsed folk category. Other Primeros Memoriales figures with conflicting star identifications are not merged here.",
        "science_summary": "The Pleiades (M45) are a nearby open cluster in Taurus. Official NASA images of the cluster are a scientific view and are not a Mexica source.",
        "story_summary": "Tianquiztli as Pleiades and New Fire timing object.",
        "astronomy_context": "M45 / Pleiades; 52-year calendar cycle.",
        "narration_lead": "In the Mexica historical sources represented here, Tianquiztli is identified with the Pleiades and used in calendrical timing, including the New Fire watch.",
        "major_objects": [PLEIADES, ALCYONE],
        "notable_deep_sky_objects": [],
        "story_order": ["pleiades", "alcyone"],
        "cosmic_signal_tags": [],
        "spectrum_tags": [],
        "media_tags": ["pleiades"],
        "shared_motifs": [
            {
                "motif_id": "pleiades_seasonal_marker",
                "tradition_story_ids": ["mexica_tianquiztli", "taurus", "maori_matariki", "arabic_peninsula_thurayya"],
                "astronomical_region": "Pleiades / M45",
                "similarity_description": "Several independent traditions use the same physical cluster as a timing object. Similarity is not a shared origin.",
                "relationship_status": "independent_similarity",
                "source_support": "Sahagún / Tezozomoc / INAH for Mexica; existing Cartography cards for Māori, Peninsula, and IAU Taurus.",
            }
        ],
        "related_story_ids": ["taurus", "maori_matariki", "arabic_peninsula_thurayya", "mexica_templo_mayor_solar"],
        "source_notes": [
            "Tezozomoc 1598 equates Tianquiztli with las Cabrillas (Pleiades).",
            "INAH and Pérez Negrete discuss Pleiades timing in the New Fire ceremony.",
            "Not merged with Maya or modern Nahua practice.",
            "Stellarium aztec pack is a name index only; its Maya Paris Codex scorpion art is not used.",
        ],
        "source_urls": [
            {
                "title": "Florentine Codex Book VII chapters 3–6 paleography",
                "institution": "UNAM / Estudios de Cultura Náhuatl",
                "url": "https://nahuatl.historicas.unam.mx/index.php/ecn/article/download/77903/68956/228837",
                "supports": "Scholarly edition of Sahagún's Nahuatl/Spanish sky and fire-drill vocabulary.",
            },
            {
                "title": "El Templo pirámide del Fuego nuevo",
                "institution": "INAH / Arqueología Mexicana",
                "url": "https://www.revistas.inah.gob.mx/index.php/arqueologia/article/download/6392/7233/12653",
                "supports": "New Fire temple at Huixachtécatl and Pleiades in the ceremony narrative.",
            },
            {
                "title": "The Temple of the New Fire at the Huixachtécatl (Hill of the Star)",
                "institution": "FAMSI",
                "url": "https://www.famsi.org/reports/01082/01082PerezNegrete01.pdf",
                "supports": "Historical reconstruction of xiuhmolpilli / New Fire at Cerro de la Estrella.",
            },
        ],
        "source_quality": "scholarly",
        "cultural_note": "Historical Mexica / colonial Nahua sources. Not a collapsed folk category and not a living Nahua classroom story.",
        "enabled": True,
    },
    {
        "id": "mexica_templo_mayor_solar",
        "story_kind": "cultural_sky_story",
        "culture_id": "mexica",
        "culture_name": "Mexica (historical)",
        "tradition_name": "historical Mexica calendrical astronomy (Templo Mayor horizon alignments)",
        "story_type": "solar_lunar_alignment",
        "evidence_type": "archaeological_inference",
        "living_tradition": False,
        "public_story_status": "public",
        "source_region": "Tenochtitlan / Basin of Mexico",
        "source_people": "historical Mexica builders and ritual specialists of Tenochtitlan",
        "canonical_name": "Templo Mayor Solar Alignments",
        "native_name": None,
        "translated_name": "Templo Mayor sunrise / Mount Tlaloc",
        "abbreviation": "",
        "aliases": ["templo mayor", "mount tlaloc sunrise", "tenochtitlan orientation"],
        "search_aliases": ["Aztec Templo Mayor", "Mexica sun alignment"],
        "sky_culture": "mexica",
        "stellarium_culture_ids": ["aztec"],
        "iau_overlap": [],
        "archaeological_context": "Measured orientations of the Templo Mayor and mountain foresights in the eastern Basin of Mexico.",
        "cultures": [
            {
                "id": "mexica",
                "name": "Mexica (historical)",
                "constellation_name": "Templo Mayor Solar Alignments",
                "mythology_summary": "Archaeological and ethnohistoric interpretations suggest the Templo Mayor and nearby peaks were used as solar-horizon calendar marks.",
                "artwork_ref": None,
            }
        ],
        "mythology_summary": "This archaeological interpretation of Mexica observations, supported by measured building orientations and Sahagún's feast calendar, suggests that sunrise alignments from the Templo Mayor toward Mount Tlaloc and other eastern peaks helped keep an agricultural year. Šprajc documented Templo Mayor solar dates; a 2022 PNAS study reconstructs Basin sunrise observatories. This is not a constellation figure and is not merged with Maya astronomy.",
        "science_summary": "Horizon astronomy uses a fixed backsight and a mountain or built foresight to catch the rising or setting Sun on chosen dates. NASA solar imagery, if shown, is a modern scientific view.",
        "story_summary": "Templo Mayor / Basin of Mexico solar horizon calendar.",
        "astronomy_context": "Solar azimuth / agricultural year.",
        "narration_lead": "This archaeological interpretation of Mexica observations suggests the Templo Mayor and eastern mountain foresights marked solar dates in the agricultural year.",
        "major_objects": [SUN],
        "notable_deep_sky_objects": [],
        "story_order": ["sun"],
        "cosmic_signal_tags": [],
        "spectrum_tags": [],
        "media_tags": ["sun"],
        "shared_motifs": [
            {
                "motif_id": "solar_horizon_or_solstice",
                "tradition_story_ids": [
                    "mexica_templo_mayor_solar",
                    "ancestral_puebloan_fajada_sun_dagger",
                    "ancestral_puebloan_holly_solstice_panel",
                ],
                "astronomical_region": "Sun",
                "similarity_description": "Independent solar-year architecture in different regions. Not a common origin.",
                "relationship_status": "independent_similarity",
                "source_support": "Šprajc 2000 and PNAS 2022 for Mexica; NPS / Sofaer 1979 for Chaco.",
            }
        ],
        "related_story_ids": ["mexica_tianquiztli"],
        "source_notes": [
            "Šprajc 2000: Templo Mayor alignments to solar horizon dates.",
            "PNAS 2022: Mount Tlaloc and other Basin sunrise landmarks.",
            "Not a Venus-Pleiades claim; Venus identifications are omitted here.",
        ],
        "source_urls": [
            {
                "title": "Ancient inhabitants of the Basin of Mexico kept an accurate agricultural calendar using sunrise observatories and mountain alignments",
                "institution": "PNAS",
                "date": "2022",
                "url": "https://www.pnas.org/doi/10.1073/pnas.2215615119",
                "supports": "Sunrise observatories and Mount Tlaloc / Templo Mayor agricultural calendar.",
            },
            {
                "title": "Archeoastronomy in Stone (comparative public framing of architectural solar time)",
                "institution": "U.S. National Park Service",
                "date": "2024-01-23",
                "url": "https://www.nps.gov/articles/000/archeoastronomy-in-stone.htm",
                "supports": "General public definition of archaeoastronomy used to keep this card in that category.",
            },
        ],
        "source_quality": "scholarly",
        "cultural_note": "Historical Mexica archaeoastronomy. Not generic Mesoamerican mythology.",
        "enabled": True,
    },
    {
        "id": "ancestral_puebloan_holly_solstice_panel",
        "story_kind": "cultural_sky_story",
        "culture_id": "ancestral_puebloan",
        "culture_name": "Ancestral Puebloan",
        "tradition_name": "Ancestral Puebloan archaeoastronomy (Hovenweep)",
        "story_type": "horizon_calendar",
        "evidence_type": "archaeological_inference",
        "living_tradition": False,
        "public_story_status": "public",
        "source_region": "Hovenweep National Monument, Utah–Colorado",
        "source_people": "Ancestral Puebloan builders of the Holly community at Hovenweep",
        "canonical_name": "Holly Solstice Panel",
        "native_name": None,
        "translated_name": "Holly summer-solstice petroglyph panel",
        "abbreviation": "",
        "aliases": ["holly petroglyph", "hovenweep solstice", "holly sun panel"],
        "search_aliases": ["Anasazi", "Ancestral Pueblo", "Ancient Puebloan"],
        "terminology_note": ANASAZI_NOTE,
        "sky_culture": "ancestral_puebloan",
        "iau_overlap": [],
        "archaeological_context": "A public NPS trail at Hovenweep's Holly Unit reaches a petroglyph panel in a boulder gap. NPS interprets a summer-solstice light beam that bisects spiral and concentric-circle marks.",
        "cultures": [
            {
                "id": "ancestral_puebloan",
                "name": "Ancestral Puebloan",
                "constellation_name": "Holly Solstice Panel",
                "mythology_summary": "Archaeological interpretations suggest the Holly petroglyph panel marked the summer solstice with a beam of light. This is not presented as a surviving oral constellation story.",
                "artwork_ref": None,
            }
        ],
        "mythology_summary": "Archaeological evidence suggests, and the National Park Service interprets, that Ancestral Puebloan observers at Hovenweep's Holly Unit marked the summer solstice on a petroglyph panel. A beam of light through a narrow gap between boulders bisects spiral and concentric-circle marks on the solstice and nearby mornings. Researchers have interpreted this as a public seasonal marker, not as a living Pueblo oral story.",
        "science_summary": "At mid-northern latitudes the rising Sun reaches its northernmost azimuth near the June solstice. A fixed gap and marked rock face can record that extreme. NASA solar imagery, if shown, is a modern scientific view and is not an Ancestral Puebloan source.",
        "story_summary": "Public NPS archaeoastronomy of the Holly summer-solstice panel.",
        "astronomy_context": "Summer-solstice sunrise azimuth; horizon calendar.",
        "narration_lead": "Archaeological evidence suggests Ancestral Puebloan observers at Hovenweep marked the summer solstice with a light beam on the Holly petroglyph panel.",
        "major_objects": [SUN],
        "notable_deep_sky_objects": [],
        "story_order": ["sun"],
        "cosmic_signal_tags": [],
        "spectrum_tags": [],
        "media_tags": ["sun"],
        "shared_motifs": [
            {
                "motif_id": "solar_horizon_or_solstice",
                "tradition_story_ids": [
                    "ancestral_puebloan_holly_solstice_panel",
                    "ancestral_puebloan_fajada_sun_dagger",
                    "mexica_templo_mayor_solar",
                ],
                "astronomical_region": "Sun / solstice",
                "similarity_description": "Independent public records of solar-year marking. Similar observational function, not a shared tradition.",
                "relationship_status": "independent_similarity",
                "source_support": "NPS Holly pages for Hovenweep; NPS / Sofaer for Chaco; PNAS 2022 for Mexica — separate sources.",
            }
        ],
        "related_story_ids": ["ancestral_puebloan_fajada_sun_dagger", "ancestral_puebloan_chaco_cardinal"],
        "source_notes": [
            "NPS Holly Petroglyph Panel: believed to mark the summer solstice.",
            "NPS Holly Group: light through a boulder gap bisects spirals and circles on and near the solstice.",
            "Lunar-standstill and Hovenweep Castle porthole claims are not added to this card.",
            "Display term is Ancestral Puebloan; Anasazi is a search alias only.",
        ],
        "source_urls": [
            {
                "title": "Holly Petroglyph Panel",
                "institution": "U.S. National Park Service, Hovenweep National Monument",
                "date": "2025-04-29",
                "url": "https://www.nps.gov/places/hollypetropanel.htm",
                "supports": "Public NPS interpretation of the Holly panel as a summer-solstice marker.",
            },
            {
                "title": "Holly Group",
                "institution": "U.S. National Park Service, Hovenweep National Monument",
                "url": "https://www.nps.gov/hove/planyourvisit/holly.htm",
                "supports": "Public trail description of the solstice light beam and descendant-community consultation context.",
            },
        ],
        "source_quality": "scholarly",
        "cultural_note": "Archaeological inference about a seasonal marker, not mythology.",
        "enabled": True,
    },
]


def main() -> None:
    raw = json.loads(REG.read_text(encoding="utf-8"))
    existing = {e["id"] for e in raw["entries"]}
    added = 0
    for entry in ENTRIES:
        if entry["id"] in existing:
            raw["entries"] = [e if e["id"] != entry["id"] else entry for e in raw["entries"]]
        else:
            raw["entries"].append(entry)
            added += 1
    REG.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {REG} added={added} total={len(raw['entries'])}")


if __name__ == "__main__":
    main()
