#!/bin/python

import lxml.etree as ET
from collections import defaultdict
import maisxml
import sys

root = ET.parse("1852_1_102_flexis.txt")

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
        # ensure file assocation elems (<REL>'s) are collected too
        sibling = child.getnext()
        descendants.append(child)
        if sibling is not None and sibling.tag == "REL":
            descendants.append(sibling)
        descendants += collect_descendants(child)
    return descendants

top_id = root.findtext("AHD/ID")
# little preamble (e.g. zaaktypeinventaris and inleiding)
preamble = root.findall(f"AHD[AHD_ID='{top_id}']")
zaaktypeinventaris = preamble[0]
# AHDS directly under zaaktypeinventaris
# TODO: Sometimes we want to split on series, but sometimes we want to splits on dossiers?
series = root.findall(f"AHD[AHD_ID='{zaaktypeinventaris.findtext("ID")}']")

# "seed" branches
branches = [[serie] for serie in series]
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
    maisxml.write_maisxml(root, f"t{idx}.txt")
