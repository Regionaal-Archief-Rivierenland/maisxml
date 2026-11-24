from lxml import etree as ET
import subprocess
from pathlib import Path
from uuid import uuid4
from datetime import datetime


def datum_gronings() -> str:
    """Huidig datum, op z'n Gronings geformateerd"""
    return datetime.now().strftime("%d-%m-%Y %H:%M %S")


def new_awe(naam: str, prompt: str, waarde: str) -> ET.Element:
    """Maak een nieuwe `<AWE>` ("flexveld")

    Args:
        - naam: de naam van het flexveld/de waarde van <NAAM>
        - prompt: de prompt van het flexveld
        - waarde: de waarde om in het flexveld te vullen
    """
    awe = ET.Element("AWE")
    awe_naam = ET.SubElement(awe, "NAAM")
    awe_prompt = ET.SubElement(awe, "PROMPT")
    awe_waarde = ET.SubElement(awe, "WAARDE")

    awe.text, awe.tail = "\n", "\n"
    awe_naam.text, awe_naam.tail = naam, "\n"
    awe_prompt.text, awe_prompt.tail = prompt, "\n"
    awe_waarde.text, awe_waarde.tail = waarde, "\n"
    return awe


def new_ahd(
    AET: str,
    top_id: str,
    parent_id: str,
    CODE: Optional[str] = None,
    by_user: Optional[str] = "RAR_ARA",
) -> ET.Element:
    """Maak een nieuwe AHD aan.

    Args:
        - AET: welke AET het is (i.e. soort van de AHD)
        - top_id: ID van de bijbehorende top
        - parent_id: Waarde van `<AHD_ID>` (i.e. het ID van de ouder van de aangemaakte AHD).
         Kan hetzelfde zijn als `top_id`.
        - CODE (optional): Eventuele waarde voor in `<CODE>` 
    """
    ahd = ET.Element("AHD")
    ET.SubElement(ahd, "ID").text = str(uuid4().int)
    ET.SubElement(ahd, "AET").text = AET
    ET.SubElement(ahd, "AHD_ID").text = parent_id
    ET.SubElement(ahd, "ADT_ID").text = "102"  # FIXME: this our organisation ID
    ET.SubElement(ahd, "AHD_ID_TOP").text = top_id
    ET.SubElement(ahd, "GUID").text = uuid4().hex.upper()
    if CODE:
        ET.SubElement(ahd, "CODE").text = "CODE"
    # TODO: do we need more?
    # voorlopig_volgnummer = ET.SubElement(ahd, "VOORLOPIG_NUMMER").text = 0
    # volgnummer = ET.SubElement(ahd, "VOLGNUMMER").text = 0

    ahd.text, ahd.tail = "\n", "\n"
    for child in ahd:
        child.tail = "\n"

    # these have the correct tail already
    date = datum_gronings()
    ahd.extend(
        (
            new_awe("USERMUTATED", "Gewijzigd door", by_user),
            new_awe("USERCREATED", "Gemaakt door", by_user),
            new_awe("DATEMUTATED", "Gewijzigd op", date),
            new_awe("DATECREATED", "Gemaakt op", date),
        )
    )

    return ahd


# Private shared helper (avoids circular dep between update_or_add_awe and touch_datemutated)
def _update_or_add_awe(ahd: ET.Element, naam: str, prompt: str, waarde: str):
    if (awe := ahd.find(f"AWE[NAAM='{naam}']")) is None:
        ahd.append(new_awe(naam, prompt, waarde))
    else:
        awe.find("WAARDE").text = waarde

def update_or_add_awe(ahd: ET.Element, naam: str, prompt: str, waarde: str):
    """Voeg een nieuwe AWE toe aan de AHD in `ahd`, *of* update de waarde van de
    huidige AWE als de AWE al bestaat.

    Update ook DATEMUTATED in `ahd`.

    Args:
        - ahd: De AHD om het flexveld aan toe te voegen
        - naam: de naam van het flexveld/de waarde van `<NAAM>`
        - prompt: de prompt van het flexveld
        - waarde: de waarde om in het flexveld te vullen
    """
    _update_or_add_awe(ahd, naam, prompt, waarde)
    touch_datemutated(ahd)


def touch_datemutated(ahd: ET.Element, by_user: str = "RAR_ARA"):
    """Update `DATEMUTATED` en `USERMUTATED`. Deze AWEs worden aangemaakt als ze nog
    niet bestaan."""
    _update_or_add_awe(ahd, "USERMUTATED", "Gewijzigd door", by_user)
    _update_or_add_awe(ahd, "DATEMUTATED", "Gewijzigd op", datum_gronings())


def extract_toegangscode(file: Path | str) -> str:
    # ignore everything but AHDs, and yield the first one after its been parsed
    _, top_ahd = next(ET.iterparse(file, tag="AHD"))
    return top_ahd.findtext("CODE")


def maisxml_has_been_fixed(file: Path | str) -> bool:
    """Check if `fixmaisxml` has been run on `file`."""
    # re-implementing `tail` in python is _truly_ annoying, but we need
    # something like it when dealing with big files, so just shell out
    tail = subprocess.check_output(["tail", file], text=True)
    if "</MFEXPORT>" in tail:
        return True
    return False


# TODO: make a proper python wrapper/fast re-implementation
def defix(file: Path | str) -> bool:
    """Undo the result of `fixmaisxml`."""
    result = subprocess.run(["fixmaisxml", "-d", file], capture_output=True, text=True)
    if result.stderr:
        raise Exception("`fixmaisxml -d` failed with:\n" + result.stderr)


def get_header(root: ET.Element | ET.ElementTree) -> list[ET.Element]:
    """Return the MAIS XML header (i.e. everything until the closing
    `</INRICHTING>`, including the top AHD)"""
    if isinstance(root, ET.ElementTree):
        root = root.getroot()

    return root[: root.index(root.find("INRICHTING")) + 1]


# TODO: maybe rename to something like copy_inrichting?
def copy_header(
    root_src: ET.Element | ET.ElementTree, root_dst: ET.Element | ET.ElementTree
):
    """Copy MAIS XML header from `root_src` to `root_dst`.

    Header here includes everything until the closing `</INRICHTING>`, including
    the top AHD. Modifies `root_dst` inplace.
    """
    if isinstance(root_src, ET.ElementTree):
        root_src = root_src.getroot()

    if isinstance(root_dst, ET.ElementTree):
        root_dst = root_dst.getroot()

    header = get_header(root_src)
    inrichting_end = root_dst.index(root_dst.find("INRICHTING")) + 1
    body = root_dst[inrichting_end:]
    root_dst = header + body

def write_maisxml(root: ET.Element, outfile: str | Path):
    """Schrijf `root` weg als MAIS XML.

    Hier is een speciale routine voor nodig omdat MAIS XML pseudo-XML is, en
    daarom aan andere regels voldoet.

    Args:
        - root (ET.Element): root-element om weg te schrijven
        - outfile (str | Path): pad naar het MAIS XML output-bestand

    Example:
        ```python
        root = ET.parse(xmlfile).getroot()

        # modify root
        # ...

        # save new tree
        maisxml.write_maisxml(root, "/path/to/output.txt")
        ```
    """
    xml_string = ET.tostring(root, encoding="utf-8").decode("utf-8")
    xml_string = xml_string.strip()
    xml_string = xml_string.removesuffix("</MFEXPORT>")
    xml_string = xml_string.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

    # MAIS outputs DOS line endings but handles unix endings fine
    with open(outfile, "w") as f:
        f.write(xml_string)
