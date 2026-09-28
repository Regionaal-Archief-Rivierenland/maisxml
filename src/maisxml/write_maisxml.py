import lxml.etree as ET
from pathlib import Path

def write_maisxml(root: ET.Element, outfile: str | Path):
    """Schrijf `root` weg als MAIS XML.

    Hier is een speciale routine voor nodig omdat MAIS XML pseudo-XML is, en
    daarom aan andere regels voldoet.
    """
    xml_string = ET.tostring(root, encoding="utf-8").decode("utf-8")
    xml_string = xml_string.removesuffix("</MFEXPORT>")
    xml_string = xml_string.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

    with open(outfile, "w", newline="\r\n") as f:
        f.write(xml_string.strip())
