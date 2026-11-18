#!/bin/python

import lxml.etree as ET
from collections import defaultdict
import maisxml
import sys
from pathlib import Path
import re

xmlfile = Path(sys.argv[1])
# xmlfile = Path("/tmp/1842_1_102_flexis.txt")
# TODO: make this a param the records the depth in the tree we want to split at
depth = 2 # 2 means: split at serie level, 3 is at dossier, etc.
toegang = re.match(r"(.+?)[_\.]", xmlfile.name)

if toegang:
    toegang = toegang.group(1)
else:
    toegang = "t" # placeholder

root = ET.parse(xmlfile)
# precompute a map that holds direct descendants of a given AHD, indexed by ID
# precompute a map between IDs and elems
parent_children_map = defaultdict(list)
for ahd in root.findall("AHD"):
    parent_id = ahd.findtext("AHD_ID")
    parent_children_map[parent_id].append(ahd)

def collect_descendants(ahd: ET.Element) -> list[ET.Element]:
    descendants = []
    ahd_id = ahd.findtext("ID")
    for child in parent_children_map[ahd_id]:
        descendants.append(child)
        # ensure file assocation elems (<REL>'s) are collected too
        sibling = child.getnext()
        if sibling is not None and sibling.tag == "REL":
            descendants.append(sibling)
        descendants += collect_descendants(child)
    return descendants

parent_id = root.findtext("AHD/ID") # id of the top
# preamble (e.g. zaaktypeinventaris and inleiding), 
# or: AETs shared by all newly splitted toegangen
preamble = []

for i in range(depth):
    # all AETs at the current depth
    horizontal_slice = parent_children_map[parent_id]
    # FIXME: this assumption is weird/often incorrect
    # assume the last node at our current depth holds the rest of the tree?
    parent_id = horizontal_slice[-1].findtext("ID")

    if i < (depth - 1):
        preamble.extend(horizontal_slice)
        

# AHDS directly under zaaktypeinventaris
# "seed" branches (i.e. collect starting points)
branches = [[AET] for AET in horizontal_slice]
# collect all descendants
for b in branches:
    b += collect_descendants(b[0])

# sort by number of children
branches.sort(key=lambda branch: len(branch))

# apppend in ABAB order
bucket_1, bucket_2 = [], []
for i in range(len(branches)):
    if i % 2:
        bucket_1.extend(branches[i])
    else:
        bucket_2.extend(branches[i])

# FIXME: update info in top relating to target toegang (e.g. name, <CODE>)
header = maisxml.get_header(root)
# re-parent (cheaper than copying)
root = ET.Element("MFEXPORT", attrib={"VERSION": "48.0", "ENCODING": "UTF-8"})
root.text = "\n"
for idx, bucket in enumerate([bucket_1, bucket_2], 1):
    root[:] = header + preamble + bucket
    nieuwe_toegangscode = f"{toegang}-{idx}"
    root.find("CODE").text = nieuwe_toegangscode
    maisxml.write_maisxml(root, xmlfile.parent / f"{nieuwe_toegangscode}.txt")
