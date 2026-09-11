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
