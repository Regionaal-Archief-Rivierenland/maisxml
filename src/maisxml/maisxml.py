from lxml import etree as ET

def new_awe(veldnaam: str, veldprompt: str, veldwaarde: str) -> ET.Element:
      """Create a new <AWE>."""
      awe = ET.Element("AWE")
      naam = ET.SubElement(awe, "NAAM")
      prompt = ET.SubElement(awe, "PROMPT")
      waarde = ET.SubElement(awe, "WAARDE")
  
      awe.text, awe.tail = "\n", "\n" # we \r\n this later
      naam.text, naam.tail = veldnaam, "\n"
      prompt.text, prompt.tail = veldprompt, "\n"
      waarde.text, waarde.tail = veldwaarde, "\n"
      return awe

def get_header(root: ET.Element) -> list[ET.Element]:
      """Return the MAIS XML header (i.e. everything until the closing
      </INRICHTING>, including the top AHD)"""

      return root[:root.index(root.find("INRICHTING")) + 1]

# TODO: maybe rename to something like copy_inrichting?
def copy_header(root_src: ET.Element, root_dst: ET.Element):
      """Copy MAIS XML header from `root_src` to `root_dst`.

      Header here includes everything  the closing </INRICHTING>, including
      the top AHD. Modifies `root_dst` inplace.
      """
      header = get_header(root_src)
      inrichting_end = root_dst.index(root_dst.find("INRICHTING")) + 1
      body = root_dst[inrichting_end:]
      root_dst = header + body
