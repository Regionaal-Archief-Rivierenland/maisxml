from lxml import etree as ET
import subprocess
from pathlib import Path

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

def is_fixed(file: Path | str) -> bool:
      """Check if `fixmaisxml` has been run on `file`."""
      # re-implementing `tail` in python is _truly_ annoying, but we need
      # something like it when dealing with big files, so just shell out
      tail = subprocess.check_output(["tail", file], text=True)
      if "</MFEXPORT>" in tail:
            return True
      return False

def get_header(root: ET.Element | ET.ElementTree) -> list[ET.Element]:
      """Return the MAIS XML header (i.e. everything until the closing
      </INRICHTING>, including the top AHD)"""
      if isinstance(root, ET.ElementTree):
            root = root.getroot()

      return root[:root.index(root.find("INRICHTING")) + 1]

# TODO: maybe rename to something like copy_inrichting?
def copy_header(root_src: ET.Element | ET.ElementTree, root_dst: ET.Element | ET.ElementTree):
      """Copy MAIS XML header from `root_src` to `root_dst`.

      Header here includes everything until the closing </INRICHTING>, including
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
