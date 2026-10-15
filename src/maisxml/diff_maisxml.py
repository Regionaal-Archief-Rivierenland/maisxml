import re
import lxml.etree as ET
import logging
from pathlib import Path
from collections import OrderedDict
from hashlib import blake2b
from concurrent.futures import ProcessPoolExecutor
from _pytest.assertion.util import _compare_eq_any
import rich
from rich.console import Console
from rich.text import Text

log = logging.getLogger(__name__)

def _show_diff(lines: list[str], context: int = 1) -> None:
    STYLES = {"-": "red", "+": "green", "?": "yellow"}
    changed = [i for i, l in enumerate(lines) if l[:1] in STYLES]
    keep = {j for i in changed for j in range(i - context, i + context + 1)}
    console = Console()
    skipped = False
    for i, line in enumerate(lines):
        if (line.startswith(" ") or line.startswith("Omitting")) and i not in keep:
            skipped = True
            continue
        if skipped:
            console.print("  ...", style="dim")
            skipped = False
        line = line.replace("Left contains", "Right contains")
        line = line.replace("Right contains", "Left contains")
        console.print(Text(line, style=STYLES.get(line[:1], "")))

# maybe make this public?
def _mais_strip(s: str):
    s = re.sub(r" +\n", "\n", s)
    s = re.sub(r"\n+", "\n", s)
    return s.strip(" ")

def _build_awe_dicts(file, SKIP) -> dict[str]:
    """Returns AWEs as key-value pairs, indexed by a digest"""
    root = ET.parse(file)
    id_digest_map, ahds = {}, {}
    for ahd in root.iterfind("AHD"):
        awes = {
            naam: _mais_strip(awe.findtext("WAARDE"))
            for awe in ahd.iterfind("AWE")
            if (naam := awe.findtext("NAAM")) not in SKIP
        }
        if code := ahd.findtext("CODE"):
            awes["CODE"] = code.strip()
        awes["AET"] = ahd.findtext("AET")

        seed = sorted(awes.keys()) + sorted(awes.values())
        digest = blake2b(''.join(seed).encode(), digest_size=16).hexdigest()
        
        id_digest_map[ahd.findtext("ID")] = digest
        mais_parent_id = ahd.findtext("AHD_ID") or ahd.findtext("ID") # Regular ID is a fallback in edgecases
        awes["parent"] = mais_parent_id
        ahds[digest] = awes

    # replace IDs by digest
    for awe in ahds.values():
        awe["parent"] = id_digest_map[awe["parent"]]

    return ahds

def diff_maisxml(old_file: str | Path, new_file: str | Path, extra_flexvelden_to_ignore: set(str) = []) -> tuple(list, list):
    """Find the differences between two MAIS XML files.

    Returns two lists of AHDs. First list contains all AHDs not present in
    `old_file`; the second contains all AHDs not in `new_file`. When comparing
    AHDs, certain flexvelden and AHD-level values will be ignored because they are
    liable to change.

    AHDs are represented as key-value dicts (e.g. `{"CODE":
    "GM0264D001", "ACHTERNAAM": "Pietersen"}` denotes the `<CODE>` and achternaam
    flexveld)

    Present or interpreting the return value is currently the job of the caller.

    Example:
       ```python
       import maisxml

       # get AHDs that are not in the old MAIS XML file, and the AHDs that are not
       # in the new MAIS XML file
       not_in_old, not_in_new = maisxml.diff_maisxml("1854.txt.old", "1854.txt.new")

       if len(not_in_old) != len(not_in_new):
           # bad news, probably
           print(f"De twee toegangen bevatten een verschillend aantal AHDs")
       ```

    Args:
        old_file (str|Path): first MAIS XML file to compare
        new_file (str|Path): second MAIS XML file to compare
        extra_flexvelden_to_ignore (Optional[list]): some flexvelden are already ignored by default;
         use this list to add more 

    Returns:
        lists: two lists; first contains all AHDs not in `old_file`, second all
         AHDs not in `new_file`
    """
    # Yes, even DATECREATED can spontaneously emerge
    SKIP = {"DATEMUTATED", "USERMUTATED", "USERCREATED", "DATECREATED"}
    SKIP.update(extra_flexvelden_to_ignore)
    old_file, new_file = Path(old_file), Path(new_file)

    with ProcessPoolExecutor() as pool:
        old, new = pool.map(_build_awe_dicts, [old_file, new_file], [SKIP, SKIP])

    not_in_old = set(new) - set(old)
    not_in_new = set(old) - set(new)
    return not_in_old, not_in_new
