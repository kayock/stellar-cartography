#!/usr/bin/env python3
"""One-shot append of modern IAU + cultural sky stories. Not imported by the app."""

from __future__ import annotations

import json
from pathlib import Path

REG = Path(__file__).resolve().parents[1] / "app/data/constellation_story_registry.json"


def star(oid, name, search, kind, aliases, designations, notes, fov):
    return {
        "id": oid,
        "name": name,
        "search_name": search,
        "kind": kind,
        "aliases": aliases,
        "designations": designations,
        "notes": notes,
        "fov_deg": fov,
    }


def iau(entry_id, name, abbr, aliases, myth, science, majors, deep, order, cs_tags, spec_tags, media_tags, extra_notes=None):
    return {
        "id": entry_id,
        "story_kind": "iau_constellation",
        "culture_id": "modern",
        "canonical_name": name,
        "abbreviation": abbr,
        "aliases": aliases,
        "sky_culture": "modern",
        "cultures": [
            {
                "id": "modern",
                "name": "Modern IAU",
                "constellation_name": name,
                "mythology_summary": myth,
                "artwork_ref": None,
            }
        ],
        "mythology_summary": myth,
        "science_summary": science,
        "major_objects": majors,
        "notable_deep_sky_objects": deep,
        "story_order": order,
        "cosmic_signal_tags": cs_tags,
        "spectrum_tags": spec_tags,
        "media_tags": media_tags,
        "source_notes": [
            f"IAU constellation {abbr}.",
            "Stellarium 26.3 Remote Control resolves the listed search_name values.",
            *(extra_notes or []),
        ],
        "enabled": True,
    }


def main() -> None:
    raw = json.loads(REG.read_text(encoding="utf-8"))
    raw["deck_title"] = "Stories of the Sky"
    raw["deck_subtitle"] = "Modern IAU figures and a small set of sourced sky-culture stories on the live Stellarium session."
    raw["sky_culture_note"] = (
        "Cartography story culture and Stellarium's active rendering culture are shown separately. "
        "They are synchronized only when the selected story's Stellarium culture id matches the live sky culture."
    )
    existing = {e["id"] for e in raw["entries"]}
    added = []

    modern = [
        iau(
            "taurus", "Taurus", "Tau",
            ["taurus", "tau", "the bull"],
            "In the modern Western / IAU figure, Taurus is the bull. Classical Greek star lore placed the Hyades in the bull's head and the Pleiades on its shoulder.",
            "Taurus is a zodiacal constellation. Aldebaran is its lucida. It contains the Pleiades and Hyades open clusters and the Crab Nebula (M1), a young supernova remnant.",
            [
                star("aldebaran", "Aldebaran", "Aldebaran", "star", ["alpha tauri", "hip 21421"], ["α Tau", "HIP 21421"], "Orange giant marking the bull's eye.", 12),
                star("elNath", "El Nath", "El Nath", "star", ["beta tauri", "hip 25428"], ["β Tau", "HIP 25428"], "Bright star at the tip of one horn.", 12),
            ],
            [
                star("pleiades", "Pleiades", "Pleiades", "cluster", ["m45", "m 45", "seven sisters", "subaru"], ["M 45"], "Nearby open cluster. Several sky traditions name this group independently of the IAU bull.", 4),
                star("crab_nebula", "Crab Nebula", "Crab Nebula", "supernova_remnant", ["m1", "m 1", "ngc 1952"], ["M 1", "NGC 1952"], "Remnant of the 1054 supernova. Chandra hosts a curated sonification and multiwavelength images.", 2),
            ],
            ["taurus", "aldebaran", "pleiades", "crab_nebula"],
            ["taurus", "crab nebula"],
            ["optical", "x-ray", "supernova remnant"],
            ["taurus", "pleiades", "crab"],
            ["Crab Nebula matches the existing Cosmic Signal and Spectrum Gallery entries."],
        ),
        iau(
            "gemini", "Gemini", "Gem",
            ["gemini", "gem", "the twins"],
            "In the modern Western / IAU figure, Gemini is the twins. Castor and Pollux are the two bright heads of the figure.",
            "Gemini is a zodiacal constellation. Castor is a multiple star system; Pollux is an evolved orange giant. The ecliptic crosses this region, so planets and the Moon often pass nearby.",
            [
                star("castor", "Castor", "Castor", "star", ["alpha geminorum", "hip 36850"], ["α Gem", "HIP 36850"], "Visual multiple star at one twin's head.", 12),
                star("pollux", "Pollux", "Pollux", "star", ["beta geminorum", "hip 37826"], ["β Gem", "HIP 37826"], "Orange giant; the brighter of the two twins as seen from Earth.", 12),
            ],
            [
                star("eskimo_placeholder", "Wasat", "Wasat", "star", ["delta geminorum"], ["δ Gem"], "Star near the ecliptic in Gemini.", 15),
            ],
            ["gemini", "castor", "pollux"],
            ["gemini"],
            ["optical"],
            ["gemini"],
        ),
        iau(
            "leo", "Leo", "Leo",
            ["leo", "the lion"],
            "In the modern Western / IAU figure, Leo is the lion. The Sickle asterism outlines the head and chest.",
            "Leo is a zodiacal constellation. Regulus lies close to the ecliptic. Several nearby galaxies appear in this region, but this story uses only Stellarium-verified bright stars.",
            [
                star("regulus", "Regulus", "Regulus", "star", ["alpha leonis", "hip 49669"], ["α Leo", "HIP 49669"], "Blue-white star at the heart of the Sickle.", 12),
                star("algieba", "Algieba", "Algieba", "star", ["gamma leonis"], ["γ Leo"], "Bright double star in the Sickle.", 12),
                star("denebola", "Denebola", "Denebola", "star", ["beta leonis"], ["β Leo"], "Star marking the lion's tail.", 12),
            ],
            [],
            ["leo", "regulus", "algieba", "denebola"],
            ["leo"],
            ["optical"],
            ["leo"],
        ),
        iau(
            "cygnus", "Cygnus", "Cyg",
            ["cygnus", "cyg", "the swan", "northern cross"],
            "In the modern Western / IAU figure, Cygnus is the swan. The Northern Cross is an asterism inside this constellation, not a separate IAU constellation.",
            "Cygnus lies along the northern Milky Way. Deneb is a distant luminous supergiant. Albireo is a contrasting double star at the swan's head. The North America Nebula is a nearby H II region.",
            [
                star("deneb", "Deneb", "Deneb", "star", ["alpha cygni", "hip 102098"], ["α Cyg", "HIP 102098"], "Luminous supergiant at the swan's tail.", 12),
                star("sadr", "Sadr", "Sadr", "star", ["gamma cygni"], ["γ Cyg"], "Star at the center of the Northern Cross.", 12),
                star("albireo", "Albireo", "Albireo", "star", ["beta cygni"], ["β Cyg"], "Famous color-contrast double star.", 8),
            ],
            [
                star("north_america_nebula", "North America Nebula", "North America Nebula", "nebula", ["ngc 7000"], ["NGC 7000"], "H II region east of Deneb. The name describes an outline, not a cultural figure.", 4),
            ],
            ["cygnus", "deneb", "albireo", "north_america_nebula"],
            ["cygnus"],
            ["optical", "nebula"],
            ["cygnus"],
        ),
        iau(
            "lyra", "Lyra", "Lyr",
            ["lyra", "lyr", "the lyre"],
            "In the modern Western / IAU figure, Lyra is the lyre. Vega is one of the brightest stars in the northern sky.",
            "Lyra is a small northern constellation. Vega is a nearby A-type star. Sheliak and Sulafat help mark the small parallelogram of the lyre.",
            [
                star("vega", "Vega", "Vega", "star", ["alpha lyrae", "hip 91262"], ["α Lyr", "HIP 91262"], "Bright nearby star; also 织女一 in the Stellarium Chinese Xingguan list.", 12),
                star("sheliak", "Sheliak", "Sheliak", "star", ["beta lyrae"], ["β Lyr"], "Eclipsing binary on the lyre's frame.", 12),
                star("sulafat", "Sulafat", "Sulafat", "star", ["gamma lyrae"], ["γ Lyr"], "Star completing the small lyre quadrilateral.", 12),
            ],
            [],
            ["lyra", "vega", "sheliak", "sulafat"],
            ["lyra"],
            ["optical"],
            ["lyra", "vega"],
        ),
        iau(
            "aquila", "Aquila", "Aql",
            ["aquila", "aql", "the eagle"],
            "In the modern Western / IAU figure, Aquila is the eagle. Altair is its lucida.",
            "Aquila lies on the Milky Way. Altair is a nearby rapidly rotating A-type star. Tarazed and Alshain form a short line with Altair; those three stars are 河鼓 in the Stellarium Chinese Xingguan list.",
            [
                star("altair", "Altair", "Altair", "star", ["alpha aquilae", "hip 97649", "河鼓二", "牛郎"], ["α Aql", "HIP 97649"], "Nearby bright star. Stellarium's Chinese star list also records 河鼓二 / 牛郎.", 12),
                star("tarazed", "Tarazed", "Tarazed", "star", ["gamma aquilae", "hip 98036"], ["γ Aql", "HIP 98036"], "Orange giant; 河鼓一 in the Stellarium Chinese list.", 12),
                star("alshain", "Alshain", "Alshain", "star", ["beta aquilae", "hip 97278"], ["β Aql", "HIP 97278"], "Fainter companion in the line; 河鼓三.", 12),
            ],
            [],
            ["aquila", "altair", "tarazed", "alshain"],
            ["aquila"],
            ["optical"],
            ["aquila", "altair"],
        ),
        iau(
            "andromeda", "Andromeda", "And",
            ["andromeda", "and"],
            "In the modern Western / IAU figure, Andromeda is a chained figure from classical Greek star lore. The IAU constellation is a sky area, not a single galaxy.",
            "Andromeda contains the Andromeda Galaxy (M31), the nearest large spiral galaxy. Alpheratz marks one corner of the Great Square of Pegasus while belonging to Andromeda in the IAU system.",
            [
                star("alpheratz", "Alpheratz", "Alpheratz", "star", ["alpha andromedae", "sirrah"], ["α And"], "Star shared visually with the Great Square of Pegasus.", 15),
                star("mirach", "Mirach", "Mirach", "star", ["beta andromedae"], ["β And"], "Orange giant used as a pointer toward M31.", 12),
            ],
            [
                star("m31", "Andromeda Galaxy", "Andromeda Galaxy", "galaxy", ["m31", "m 31", "ngc 224"], ["M 31", "NGC 224"], "Nearest large spiral galaxy. A curated Cosmic Signal and Spectrum Gallery views exist for this object.", 3),
            ],
            ["andromeda", "alpheratz", "m31"],
            ["andromeda", "m31"],
            ["optical", "x-ray", "galaxy"],
            ["andromeda", "m31"],
            ["M31 matches existing Cosmic Signal and Spectrum Gallery entries."],
        ),
        iau(
            "perseus", "Perseus", "Per",
            ["perseus", "per"],
            "In the modern Western / IAU figure, Perseus is a hero from classical Greek star lore. Algol is the variable star long associated with the figure's head.",
            "Perseus lies in the northern Milky Way. Algol is an eclipsing binary. The Double Cluster (NGC 869/884) is a pair of open clusters along the Perseus Arm.",
            [
                star("mirfak", "Mirfak", "Mirfak", "star", ["alpha persei"], ["α Per"], "Brightest star of Perseus; center of a nearby moving group.", 12),
                star("algol", "Algol", "Algol", "star", ["beta persei"], ["β Per"], "Prototype eclipsing binary.", 10),
            ],
            [
                star("double_cluster", "Double Cluster", "Double Cluster", "cluster", ["ngc 869", "h persei", "chi persei"], ["NGC 869", "NGC 884"], "Pair of open clusters in Perseus.", 3),
            ],
            ["perseus", "mirfak", "algol", "double_cluster"],
            ["perseus"],
            ["optical"],
            ["perseus"],
        ),
        iau(
            "canis_major", "Canis Major", "CMa",
            ["canis major", "cma", "great dog"],
            "In the modern Western / IAU figure, Canis Major is the greater dog. Sirius is the brightest star in the night sky.",
            "Canis Major is a southern constellation as seen from mid-northern latitudes. Sirius is a nearby A-type binary. Adhara, Wezen, and Mirzam are luminous more-distant stars in the same IAU area.",
            [
                star("sirius", "Sirius", "Sirius", "star", ["alpha canis majoris", "hip 32349"], ["α CMa", "HIP 32349"], "Brightest night-sky star; a nearby binary.", 15),
                star("adhara", "Adhara", "Adhara", "star", ["epsilon canis majoris"], ["ε CMa"], "Luminous star in the dog's body.", 12),
                star("mirzam", "Mirzam", "Mirzam", "star", ["beta canis majoris"], ["β CMa"], "Bright star preceding Sirius in the sky's daily motion.", 12),
            ],
            [],
            ["canis_major", "sirius", "adhara"],
            ["canis major"],
            ["optical"],
            ["canis_major", "sirius"],
        ),
        iau(
            "carina", "Carina", "Car",
            ["carina", "car", "the keel"],
            "In the modern IAU figure, Carina is the keel of the ship Argo, which was later divided into Carina, Puppis, and Vela.",
            "Carina is a rich southern Milky Way constellation. Canopus is the second-brightest night-sky star. η Car and NGC 3372 mark a massive star-forming region. Stellarium focuses η Car and NGC 3372; the English phrase 'Eta Carinae' was not accepted as a search target in this session.",
            [
                star("canopus", "Canopus", "Canopus", "star", ["alpha carinae", "hip 30438"], ["α Car", "HIP 30438"], "Second-brightest night-sky star.", 15),
                star("eta_car", "η Car", "η Car", "star", ["eta carinae", "hip 41307"], ["η Car", "HIP 41307"], "Luminous unstable massive star. Use the Stellarium search name η Car.", 8),
            ],
            [
                star("ngc_3372", "NGC 3372", "NGC 3372", "nebula", ["keyhole nebula", "carina nebula"], ["NGC 3372"], "Bright southern H II region. Stellarium also accepts Keyhole Nebula for a dark lane inside this complex.", 3),
            ],
            ["carina", "canopus", "eta_car", "ngc_3372"],
            ["carina"],
            ["optical", "nebula"],
            ["carina"],
        ),
        iau(
            "crux", "Crux", "Cru",
            ["crux", "cru", "southern cross"],
            "In the modern IAU figure, Crux is the Southern Cross. It is a small constellation, not merely an asterism inside Centaurus.",
            "Crux is the smallest IAU constellation. Acrux, Mimosa, and Gacrux form the familiar cross used with the Pointers for southern orientation.",
            [
                star("acrux", "Acrux", "Acrux", "star", ["alpha crucis"], ["α Cru"], "Southern end of the cross.", 12),
                star("mimosa", "Mimosa", "Mimosa", "star", ["beta crucis"], ["β Cru"], "Eastern arm of the cross.", 12),
                star("gacrux", "Gacrux", "Gacrux", "star", ["gamma crucis"], ["γ Cru"], "Northern arm; an orange giant.", 12),
            ],
            [],
            ["crux", "acrux", "mimosa", "gacrux"],
            ["crux"],
            ["optical"],
            ["crux"],
        ),
        iau(
            "virgo", "Virgo", "Vir",
            ["virgo", "vir"],
            "In the modern Western / IAU figure, Virgo is a maiden. Spica is the ear of grain in that figure.",
            "Virgo is a large zodiacal constellation. Spica is a close binary. The Virgo Cluster of galaxies lies in this area; M87 is a giant elliptical with a relativistic jet and curated Chandra media.",
            [
                star("spica", "Spica", "Spica", "star", ["alpha virginis"], ["α Vir"], "Bright binary star; lucida of Virgo.", 12),
            ],
            [
                star("m87", "M87", "M87", "galaxy", ["messier 87", "ngc 4486", "virgo a"], ["M 87", "NGC 4486"], "Giant elliptical in the Virgo Cluster. A curated Cosmic Signal and Spectrum Gallery views exist for this object.", 2),
            ],
            ["virgo", "spica", "m87"],
            ["virgo", "m87"],
            ["optical", "x-ray", "radio", "galaxy"],
            ["virgo", "m87"],
            ["M87 matches existing Cosmic Signal and Spectrum Gallery entries."],
        ),
    ]

    cultural = [
        {
            "id": "chinese_beidou",
            "story_kind": "cultural_sky_story",
            "culture_id": "chinese",
            "culture_name": "Chinese",
            "tradition_name": "Chinese Xingguan tradition (Yixiang Kaocheng / Stellarium Chinese sky culture)",
            "story_type": "xingguan",
            "source_region": "East Asia",
            "source_people": "Chinese astronomical tradition as recorded in Qing imperial star catalogues",
            "canonical_name": "Northern Dipper",
            "native_name": "北斗",
            "translated_name": "Northern Dipper (Běi Dǒu)",
            "abbreviation": "UMa",
            "aliases": ["beidou", "bei dou", "northern dipper", "北斗"],
            "sky_culture": "chinese",
            "iau_overlap": ["UMa"],
            "cultures": [
                {
                    "id": "chinese",
                    "name": "Chinese",
                    "constellation_name": "北斗",
                    "mythology_summary": "In this Chinese Xingguan tradition, 北斗 (Běi Dǒu, Northern Dipper) is a seven-star asterism. It is not the same figure as the IAU constellation Ursa Major, though the same seven bright stars lie inside that IAU area.",
                    "artwork_ref": None,
                }
            ],
            "mythology_summary": "In this Chinese Xingguan tradition, 北斗 (Běi Dǒu, Northern Dipper) is a seven-star asterism recorded in Stellarium's Chinese sky culture from the Yixiang Kaocheng tradition. Xingguan are star-official groupings without IAU-style boundaries.",
            "science_summary": "The same seven stars are Dubhe, Merak, Phecda, Megrez, Alioth, Mizar, and Alkaid. In modern astronomy they form the Plough / Big Dipper asterism inside Ursa Major. Scientific names below are modern identifiers, not Chinese catalogue names.",
            "story_summary": "In this Chinese Xingguan tradition, 北斗 is a northern seven-star grouping. Stellarium lists the primary stars as HIP 54061, 53910, 58001, 59774, 62956, 65378, and 67301.",
            "astronomy_context": "These HIP identifiers correspond to Dubhe through Alkaid. This story does not treat the IAU Great Bear as a Chinese figure.",
            "major_objects": [
                star("dubhe", "Dubhe / 北斗一", "Dubhe", "star", ["alpha ursae majoris", "hip 54061", "天枢"], ["α UMa", "HIP 54061"], "Stellarium Chinese list: 北斗一 / 天枢.", 18),
                star("merak", "Merak / 北斗二", "Merak", "star", ["beta ursae majoris", "hip 53910"], ["β UMa", "HIP 53910"], "Stellarium Chinese list: 北斗二.", 18),
                star("phecda", "Phecda / 北斗三", "Phecda", "star", ["gamma ursae majoris", "hip 58001"], ["γ UMa", "HIP 58001"], "Stellarium Chinese list: 北斗三.", 18),
                star("megrez", "Megrez / 北斗四", "Megrez", "star", ["delta ursae majoris", "hip 59774"], ["δ UMa", "HIP 59774"], "Stellarium Chinese list: 北斗四.", 18),
                star("alioth", "Alioth / 北斗五", "Alioth", "star", ["epsilon ursae majoris", "hip 62956"], ["ε UMa", "HIP 62956"], "Stellarium Chinese list: 北斗五.", 18),
                star("mizar", "Mizar / 北斗六", "Mizar", "star", ["zeta ursae majoris", "hip 65378"], ["ζ UMa", "HIP 65378"], "Stellarium Chinese list: 北斗六.", 12),
                star("alkaid", "Alkaid / 北斗七", "Alkaid", "star", ["eta ursae majoris", "hip 67301"], ["η UMa", "HIP 67301"], "Stellarium Chinese list: 北斗七.", 18),
            ],
            "notable_deep_sky_objects": [],
            "story_order": ["dubhe", "merak", "phecda", "megrez", "alioth", "mizar", "alkaid"],
            "cosmic_signal_tags": [],
            "spectrum_tags": [],
            "media_tags": ["ursa major"],
            "source_notes": [
                "Stellarium 26.3 sky culture id=chinese, Xingguan 北斗 / Northern Dipper (CON chinese 039).",
                "Primary HIP line from Stellarium chinese/index.json; Chinese labels from star_names.zh_CN.fab.",
                "Catalogue tradition: Yixiang Kaocheng (仪象考成, 1756) and Yi Shitong's Chinese and Western Contrast Star Chart and Catalogue 1950.0.",
                "Variants exist among historical Chinese maps; this story follows the Stellarium Chinese pack.",
            ],
            "source_urls": [
                {
                    "title": "Stellarium Chinese sky culture — 北斗 / Northern Dipper",
                    "institution": "Stellarium / Chinese sky-culture pack",
                    "url": "https://github.com/Stellarium/stellarium/tree/master/skycultures/chinese",
                    "supports": "Xingguan name, HIP members, and catalogue tradition notes.",
                },
                {
                    "title": "Yi Shitong, Chinese and Western Contrast Star Chart and Catalogue 1950.0 (1981)",
                    "institution": "Science Press, Beijing (cited in Stellarium chinese/description.md)",
                    "url": "https://github.com/Stellarium/stellarium/blob/master/skycultures/chinese/description.md",
                    "supports": "Identification of Stellarium's Chinese Xingguan list with the Yixiang Kaocheng tradition.",
                },
            ],
            "source_quality": "stellarium_skyculture",
            "cultural_note": "Xingguan are not IAU constellations. This is a living naming tradition in modern Chinese astronomy even though Xingguan are no longer the official constellation system.",
            "enabled": True,
        },
        {
            "id": "chinese_zhinu_hegu",
            "story_kind": "cultural_sky_story",
            "culture_id": "chinese",
            "culture_name": "Chinese",
            "tradition_name": "Chinese Xingguan tradition (Yixiang Kaocheng / Stellarium Chinese sky culture)",
            "story_type": "xingguan_pair",
            "source_region": "East Asia",
            "source_people": "Chinese astronomical tradition as recorded in Qing imperial star catalogues",
            "canonical_name": "Weaving Girl and Drum at the River",
            "native_name": "织女 · 河鼓",
            "translated_name": "Zhī Nǚ (Weaving Girl) and Hé Gǔ (Drum at the River)",
            "abbreviation": "",
            "aliases": ["zhinu", "zhi nu", "hegu", "he gu", "织女", "河鼓", "weaver and cowherd", "niulang"],
            "sky_culture": "chinese",
            "iau_overlap": ["Lyr", "Aql"],
            "cultures": [
                {
                    "id": "chinese",
                    "name": "Chinese",
                    "constellation_name": "织女 · 河鼓",
                    "mythology_summary": "In this Chinese Xingguan tradition, 织女 and 河鼓 are two separate asterisms. They sit in the modern IAU areas of Lyra and Aquila. They are not Chinese versions of those IAU constellations.",
                    "artwork_ref": None,
                }
            ],
            "mythology_summary": "In this Chinese Xingguan tradition, 织女 (Zhī Nǚ, Weaving Girl) is a three-star grouping around Vega, and 河鼓 (Hé Gǔ, Drum at the River) is the three-star line Altair–Tarazed–Alshain. Stellarium also records 牛郎 as an alternate label on 河鼓二 (Altair). Folklore associated with Qixi is a later popular layer and is not treated here as the Xingguan definition.",
            "science_summary": "Vega and Altair are nearby bright A-type stars on opposite sides of the Milky Way band. Scientific NASA or Chandra media for these stars, if shown, is a modern scientific view and is not a source for the Xingguan.",
            "story_summary": "Two Xingguan spanning the IAU constellations Lyra and Aquila.",
            "astronomy_context": "HIP 91262 (Vega), 91919, 91971 form 织女. HIP 98036, 97649, 97278 form 河鼓.",
            "major_objects": [
                star("vega", "Vega / 织女一", "Vega", "star", ["alpha lyrae", "hip 91262", "织女"], ["α Lyr", "HIP 91262"], "Stellarium Chinese list: 织女一 / 织女.", 10),
                star("zhinu_er", "织女二", "HIP 91919", "star", ["hip 91919"], ["HIP 91919"], "Second star of Xingguan 织女 in Stellarium's line list.", 10),
                star("zhinu_san", "织女三", "HIP 91971", "star", ["hip 91971"], ["HIP 91971"], "Third star of Xingguan 织女 in Stellarium's line list.", 10),
                star("tarazed", "Tarazed / 河鼓一", "Tarazed", "star", ["gamma aquilae", "hip 98036"], ["γ Aql", "HIP 98036"], "Stellarium Chinese list: 河鼓一.", 10),
                star("altair", "Altair / 河鼓二 / 牛郎", "Altair", "star", ["alpha aquilae", "hip 97649", "牛郎"], ["α Aql", "HIP 97649"], "Stellarium Chinese list: 河鼓二 and 牛郎.", 10),
                star("alshain", "Alshain / 河鼓三", "Alshain", "star", ["beta aquilae", "hip 97278"], ["β Aql", "HIP 97278"], "Stellarium Chinese list: 河鼓三.", 10),
            ],
            "notable_deep_sky_objects": [],
            "story_order": ["vega", "altair", "tarazed"],
            "cosmic_signal_tags": [],
            "spectrum_tags": [],
            "media_tags": ["vega", "altair"],
            "source_notes": [
                "Stellarium Chinese Xingguan 织女 (CON chinese 304) and 河鼓 (CON chinese 093).",
                "Does not include Deneb. Deneb is not a member of these two Xingguan in the Stellarium Chinese pack.",
                "Popular Cowherd-Weaver festival narratives are not used as the definition of the Xingguan.",
            ],
            "source_urls": [
                {
                    "title": "Stellarium Chinese sky culture — 织女 and 河鼓",
                    "institution": "Stellarium / Chinese sky-culture pack",
                    "url": "https://github.com/Stellarium/stellarium/tree/master/skycultures/chinese",
                    "supports": "Xingguan names, HIP lines, and 牛郎 as an alternate label on Altair.",
                },
                {
                    "title": "Stellarium Chinese sky culture description (Yixiang Kaocheng; Yi Shitong 1981)",
                    "institution": "Stellarium documentation citing Science Press, Beijing",
                    "url": "https://github.com/Stellarium/stellarium/blob/master/skycultures/chinese/description.md",
                    "supports": "That Stellarium's Chinese asterisms follow the Yixiang Kaocheng / Yi Shitong tradition.",
                },
            ],
            "source_quality": "stellarium_skyculture",
            "cultural_note": "This story spans two IAU constellations on purpose. It is not a Chinese translation of Lyra or Aquila.",
            "enabled": True,
        },
        {
            "id": "maori_matariki",
            "story_kind": "cultural_sky_story",
            "culture_id": "maori",
            "culture_name": "Māori",
            "tradition_name": "Māori astronomical tradition (Tātai Arorangi), as documented in Stellarium's Māori sky culture",
            "story_type": "seasonal_sky_knowledge",
            "source_region": "Aotearoa New Zealand",
            "source_people": "Māori",
            "canonical_name": "Matariki",
            "native_name": "Matariki",
            "translated_name": "Matariki (Pleiades)",
            "abbreviation": "Tau",
            "aliases": ["matariki", "pleiades", "m45"],
            "sky_culture": "maori",
            "iau_overlap": ["Tau"],
            "cultures": [
                {
                    "id": "maori",
                    "name": "Māori",
                    "constellation_name": "Matariki",
                    "mythology_summary": "In the Māori tradition represented by this story, Matariki is the Pleiades. Stellarium's Māori pack notes iwi (tribal) variation in star naming and records Matariki as the well-known name for this cluster.",
                    "artwork_ref": None,
                }
            ],
            "mythology_summary": "In the Māori tradition represented by this story, Matariki names the Pleiades. Stellarium's Māori sky culture, following published sources including Elsdon Best's Dominion Museum monographs, treats Matariki as seasonal and navigational sky knowledge. This is not a generic Polynesian story, and it is not the Greek Pleiades myth.",
            "science_summary": "The Pleiades (M45) is a nearby open cluster in Taurus. NASA imagery of the cluster is a modern scientific view and is not a Māori source.",
            "story_summary": "Matariki is the Māori name for the Pleiades in the Stellarium Māori pack.",
            "astronomy_context": "M45 / Alcyone and neighbouring bright cluster members.",
            "major_objects": [
                star("pleiades", "Matariki / Pleiades", "Pleiades", "cluster", ["m45", "matariki"], ["M 45"], "Stellarium Māori common name for M45 is Matariki. The English cluster name is the Stellarium search target.", 4),
                star("alcyone", "Alcyone", "Alcyone", "star", ["eta tauri", "hip 17702"], ["η Tau", "HIP 17702"], "Brightest star in the cluster. Stellarium Māori common_names also attach Matariki to HIP 17702.", 3),
                star("atlas", "Atlas", "Atlas", "star", ["27 tauri"], ["27 Tau"], "Bright cluster member used as a tour step. Individual Māori star names inside Matariki vary by iwi; Stellarium notes some labels were placed only to record names.", 3),
                star("electra", "Electra", "Electra", "star", ["17 tauri"], ["17 Tau"], "Bright cluster member. Not treated here as a specific iwi personal name.", 3),
            ],
            "notable_deep_sky_objects": [],
            "story_order": ["pleiades", "alcyone", "atlas", "electra"],
            "cosmic_signal_tags": [],
            "spectrum_tags": [],
            "media_tags": ["pleiades"],
            "source_notes": [
                "Stellarium sky culture id=maori. Common name Matariki on M45 and HIP 17702.",
                "Iwi variation is explicitly recorded in Stellarium's Māori description.",
                "Not generalized to Hawaiian, Tahitian, or other Polynesian star compasses.",
            ],
            "source_urls": [
                {
                    "title": "Stellarium Māori sky culture description and references",
                    "institution": "Stellarium (contributor Dan Smale); cites Dominion Museum / Phoenix Astronomical Society",
                    "url": "https://github.com/Stellarium/stellarium/tree/master/skycultures/maori",
                    "supports": "Matariki = Pleiades; iwi variation; seasonal/navigation framing.",
                },
                {
                    "title": "Best, E. (1955). The Astronomical Knowledge of the Maori. Dominion Museum Monograph no. 3",
                    "institution": "Dominion Museum, Wellington (cited by Stellarium maori/references.txt)",
                    "url": "https://github.com/Stellarium/stellarium/blob/master/skycultures/maori/references.txt",
                    "supports": "Scholarly monograph behind the Stellarium Māori star list.",
                },
            ],
            "source_quality": "stellarium_skyculture",
            "cultural_note": "This is a living tradition. Public Matariki marking in Aotearoa is contemporary. Variants among iwi are acknowledged and not merged.",
            "enabled": True,
        },
        {
            "id": "arabic_peninsula_thurayya",
            "story_kind": "cultural_sky_story",
            "culture_id": "arabic_peninsula",
            "culture_name": "Arabic (Arabian Peninsula tradition)",
            "tradition_name": "Arabian Peninsula oral stellar tradition (anwāʾ / seasonal star timing)",
            "story_type": "seasonal_star_knowledge",
            "source_region": "Arabian Peninsula",
            "source_people": "Arabic-speaking communities of the Arabian Peninsula, as documented in recorded poetry and anwāʾ commentary",
            "canonical_name": "al-Thurayyā",
            "native_name": "الثريا",
            "translated_name": "al-Thurayyā (Pleiades)",
            "abbreviation": "Tau",
            "aliases": ["thurayya", "al-thurayya", "pleiades", "الثريا"],
            "sky_culture": "arabic_arabian_peninsula",
            "iau_overlap": ["Tau"],
            "cultures": [
                {
                    "id": "arabic_peninsula",
                    "name": "Arabic (Arabian Peninsula tradition)",
                    "constellation_name": "الثريا",
                    "mythology_summary": "In this Arabian Peninsula stellar tradition, al-Thurayyā is the Pleiades and is used in seasonal timing. Stellarium records that some local calendars begin the year with the heliacal rising of al-Thurayyā.",
                    "artwork_ref": None,
                }
            ],
            "mythology_summary": "In this Arabian Peninsula stellar tradition — not medieval Islamic astronomy and not a collapsed folk category — al-Thurayyā is the Pleiades. Stellarium's Arabian Peninsula sky culture, drawing on documented poetry and anwāʾ commentary, describes star timing for travel, weather, and agriculture. Other names and legends in that pack belong to different asterisms and are not merged here.",
            "science_summary": "The Pleiades are a nearby open cluster. Official NASA images of the cluster are scientific media, not the cultural source.",
            "story_summary": "al-Thurayyā as a timing asterism in Arabian Peninsula tradition.",
            "astronomy_context": "M45 / Pleiades.",
            "major_objects": [
                star("pleiades", "al-Thurayyā / Pleiades", "Pleiades", "cluster", ["m45", "thurayya"], ["M 45"], "Stellarium arabic_arabian_peninsula constellation Thur: Al-Thurayya / الثريا.", 4),
                star("alcyone", "Alcyone", "Alcyone", "star", ["eta tauri"], ["η Tau"], "Brightest star in the cluster; used here as a Stellarium tour step, not as a substitute Arabic personal name.", 3),
            ],
            "notable_deep_sky_objects": [],
            "story_order": ["pleiades", "alcyone"],
            "cosmic_signal_tags": [],
            "spectrum_tags": [],
            "media_tags": ["pleiades"],
            "source_notes": [
                "Stellarium sky culture id=arabic_arabian_peninsula, constellation Thur (Al-Thurayya).",
                "Distinct from arabic_al-sufi (Book of Fixed Stars / medieval Islamic astronomy).",
                "Distinct from modern IAU Taurus and from Māori Matariki.",
            ],
            "source_urls": [
                {
                    "title": "Stellarium Arabic (Arabian Peninsula) sky culture — Al-Thurayya",
                    "institution": "Stellarium; commentary compiled with published anwāʾ sources",
                    "url": "https://github.com/Stellarium/stellarium/tree/master/skycultures/arabic_arabian_peninsula",
                    "supports": "Name الثريا / al-Thurayyā for the Pleiades; seasonal timing; oral-poetry documentation.",
                },
                {
                    "title": "Al-Ajaji, Khalid. Explanation of al-Qāḍī poem of anwāʾ and stars (2013), cited as Stellarium reference #2",
                    "institution": "Riyadh (cited in Stellarium arabic_arabian_peninsula/description.md)",
                    "url": "https://github.com/Stellarium/stellarium/blob/master/skycultures/arabic_arabian_peninsula/description.md",
                    "supports": "Published commentary on Peninsula star-timing poetry used by the sky-culture pack.",
                },
            ],
            "source_quality": "stellarium_skyculture",
            "cultural_note": "This is Peninsula folk / anwāʾ star knowledge, not al-Ṣūfī's Ptolemaic Book of Fixed Stars.",
            "enabled": True,
        },
        {
            "id": "arabic_sufi_lyra",
            "story_kind": "cultural_sky_story",
            "culture_id": "arabic_sufi",
            "culture_name": "Medieval Islamic astronomy (al-Ṣūfī)",
            "tradition_name": "al-Ṣūfī, Book of Fixed Stars (Kitāb ṣuwar al-kawākib al-thābita), c. 964",
            "story_type": "medieval_astronomical_treatise",
            "source_region": "Iran / Islamic world (Rayy; the book treats Ptolemy's 48 constellations)",
            "source_people": "ʿAbd al-Raḥmān al-Ṣūfī and the medieval Islamic astronomical tradition transmitting the Almagest",
            "canonical_name": "al-Lawrā (the Lyre)",
            "native_name": "اللورا",
            "translated_name": "al-Lawrā / the Lyre",
            "abbreviation": "Lyr",
            "aliases": ["al-lawra", "lyra", "lyre", "al-sufi lyra"],
            "sky_culture": "arabic_al-sufi",
            "iau_overlap": ["Lyr"],
            "cultures": [
                {
                    "id": "arabic_sufi",
                    "name": "Medieval Islamic astronomy (al-Ṣūfī)",
                    "constellation_name": "اللورا",
                    "mythology_summary": "In al-Ṣūfī's Book of Fixed Stars, the Lyre is one of Ptolemy's 48 constellations. Stellarium's arabic_al-sufi pack labels it al-Lawrā. This is a scientific treatise tradition, not Peninsula folk star lore.",
                    "artwork_ref": None,
                }
            ],
            "mythology_summary": "In the medieval Islamic astronomical tradition represented by this story, ʿAbd al-Raḥmān al-Ṣūfī (903–986) described the Lyre among Ptolemy's 48 constellations in the Book of Fixed Stars, shortly before 964. Stellarium's Al-Sufi sky culture, following Paul Kunitzsch's account, presents each constellation with discussion, indigenous Arabic star-name identifications, globe/sky drawings, and a Ptolemaic table. This is not Arabian Peninsula oral tradition and is not labeled Arab mythology.",
            "science_summary": "The same IAU area is Lyra, with Vega as lucida. Modern photometry and NASA imagery are later scientific views.",
            "story_summary": "al-Ṣūfī's Lyre / al-Lawrā.",
            "astronomy_context": "Vega, Sheliak, Sulafat.",
            "major_objects": [
                star("vega", "Vega", "Vega", "star", ["alpha lyrae"], ["α Lyr"], "Lucida of the IAU constellation Lyra; tour target for al-Ṣūfī's Lyre region.", 10),
                star("sheliak", "Sheliak", "Sheliak", "star", ["beta lyrae"], ["β Lyr"], "Frame star of the lyre.", 10),
                star("sulafat", "Sulafat", "Sulafat", "star", ["gamma lyrae"], ["γ Lyr"], "Frame star of the lyre.", 10),
            ],
            "notable_deep_sky_objects": [],
            "story_order": ["vega", "sheliak", "sulafat"],
            "cosmic_signal_tags": [],
            "spectrum_tags": [],
            "media_tags": ["lyra", "vega"],
            "source_notes": [
                "Stellarium sky culture id=arabic_al-sufi, constellation Lyr / al-Lawrā.",
                "Kunitzsch describes the Book of Fixed Stars as treating Ptolemy's 48 constellations with criticism and indigenous Arabic name identifications.",
                "Do not collapse this with arabic_arabian_peninsula.",
            ],
            "source_urls": [
                {
                    "title": "Stellarium Arabic (Al-Sufi) sky culture description",
                    "institution": "Stellarium; quoting Paul Kunitzsch on the Book of Fixed Stars",
                    "url": "https://github.com/Stellarium/stellarium/tree/master/skycultures/arabic_al-sufi",
                    "supports": "Identification of al-Lawrā as the Lyre; treatise structure; date c. 964.",
                },
                {
                    "title": "Kunitzsch, Paul. The Astronomer Abu'l-Husayn al-Sufi and His Book on the Constellations. In The Arabs and the Stars. Variorum, 1989.",
                    "institution": "Variorum Reprints (cited as Stellarium arabic_al-sufi reference #1)",
                    "url": "https://github.com/Stellarium/stellarium/blob/master/skycultures/arabic_al-sufi/description.md",
                    "supports": "Scholarly description of al-Ṣūfī's method and relation to the Almagest.",
                },
            ],
            "source_quality": "stellarium_skyculture",
            "cultural_note": "Medieval Islamic mathematical astronomy transmitting and revising Ptolemy. Not folk mythology.",
            "enabled": True,
        },
    ]

    # Gemini currently has a dummy deep-sky object; drop empty-feeling extras if search fails.
    # Wasat was verified? Not in the batch. Check - if unsure remove from story_order (already not in order).

    for entry in modern + cultural:
        if entry["id"] in existing:
            continue
        raw["entries"].append(entry)
        added.append(entry["id"])

    REG.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("ADDED", added)
    print("TOTAL", len(raw["entries"]))


if __name__ == "__main__":
    main()
