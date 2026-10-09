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

def diff_mais_xml(old_file: str | Path, new_file: str | Path, skip_extra: set[str] = []):
    # Yes, even DATECREATED can spontaneously emerge
    SKIP = {"DATEMUTATED", "USERMUTATED", "USERCREATED", "DATECREATED"}
    SKIP.update(skip_extra)
    old_file, new_file = Path(old_file), Path(new_file)
    
    with ProcessPoolExecutor() as pool:
        old, new = pool.map(_build_awe_dicts, [old_file, new_file], [SKIP, SKIP])

    if len(old) != len(new):
        not_in_old = set(new) - set(old)
        not_in_new = set(old) - set(new)
        # TODO: no idea how to represent this
        log.error(f"{old_file.name} contains {len(old)} AETs, but {new_file.name} contains {len(new)}.")
        if not_in_old:
            log.error(f"AETs not in {old_file.name}:")
            for aet in not_in_old:
                rich.print(aet)
        if not_in_new:
            log.error(f"AETs not in {new_file.name}:")
            for aet in not_in_new:
                rich.print(aet)
        log.error("Note that there might be differences *within* AETs, still!")
    else:
        for digest1, digest2 in zip(old, new):
            if digest1 != digest2:
                awes_old, awes_new = old[digest1], new[digest2]
                # sort the dicts before diffing
                awes_old = {key: awes_old[key] for key in sorted(awes_old.keys())}
                awes_new = {key: awes_new[key] for key in sorted(awes_new.keys())}
                diff_lines = _compare_eq_any(
                    awes_new,
                    awes_old,
                    lambda s, lexer="": s,
                    verbose=1,
                    assertion_text_diff_style="ndiff",
                )
                _show_diff(list(diff_lines))





