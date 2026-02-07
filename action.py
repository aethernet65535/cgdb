import gdb
import os
import sys
import itertools
import time
import threading

from dataclasses import dataclass, field
from typing import Callable

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from config import *
from color_debug import *
from global_var import *
from const import *
from main import *

# ======================
# === --- ACTION --- ===
# ======================
#
# --- Utils ---
def action_free(cbs):
    global cargo_cbs, framep_to_root_cbs

    if cbs is None:
        pr_err("finish_free: cbs is None")
        return False

    curr_rid = cbs.rid

    root = find_root(cbs.archetype)
    if root is None:
        pr_err("finish_free: root is None")
        return False

    framep = root.framep
    
    cargo_cbs = {
        k: v \
        for k, v in cargo_cbs.items() \
        if v.rid != curr_rid
    }
    framep_to_root_cbs = {
            k: v \
            for k, v in framep_to_root_cbs.items() \
            if v.framep != framep
    }

    pr_debug("finish_free: DONE!")
    return True

## --- Toys ---
#
# Needed:
# - paper with `count` field.
def action_count(cbs):
    try:
        paper = cbs.archetype.paper
    except:
        pr_err("all_count: paper is None")
        return None

    try:
        paper.count += 1

        return paper.count
    except:
        pr_err("all_count: paper.count is not exist")
        return None

## --- Specific ---
def action_name_count(cbs):
    count = action_count(cbs)
    if count is None:
        return None

    name = cbs.archetype.bp_name

    pr_log("="*80)
    pr_log(f"{name}: count = {count}")
    pr_log("="*80)

def action_box(cbs):
    elf_map_log(cbs.rid)
    action_free(cbs)

### --- CHART GENERATE ---
def walk_count():
    lbox_count = []
    have_data = 0

    for bps in cargo_bps.values():
        if not bps.paper:
            continue

        try:
            bp_name = bps.bp_name
            count = bps.paper.count
        except:
            pass

        if count < 0:
            pr_err(f"walk_count: invalid count: {count}")

        if not have_data:
            have_data = 1
        create_count(bp_name, count, lbox_count)

    if have_data:
        return lbox_count
    else:
        return None

def create_count(bp_name, count, lbox_count):
    entity = BreakpointCount(
        bp_name = bp_name,
        count = count
    )

    lbox_count.append(entity)

def calc_block_size(max_count):
    if max_count < 0:
        return -1

    ret = (50 / max_count)
    return ret

def find_max_count(lbox_count, is_reverse):
    if is_reverse:
        return lbox_count[0].count
    else:
        max_count = None
        for entity in lbox_count:
            count = entity.count
            max_count = max(count, max_count)

        return max_count

def action_generate_count_chart(cbs):
    is_reverse = 1

    lbox_count = walk_count()
    if not lbox_count:
        return None
    
    if is_reverse:
        lbox_count.sort(key=lambda x: x.count, reverse=True)
    
    max_count = find_max_count(lbox_count, is_reverse)
    if max_count is None:
        pr_err("max_count is None")
        return None

    block_size = calc_block_size(max_count)
    if block_size < 0:
        return None

    pr_log("Result: [Function Called Times]")
    pr_log("=" * 80)
    _generate_count_chart(lbox_count, block_size)
    pr_log("")

def _generate_count_chart(lbox_count, block_size):
    for entity in lbox_count:
        bp_name = entity.bp_name
        count = entity.count
        block = count * block_size
        if count > 0:
            block = max(1, int(block))

        block = int(block)
        block_pr = "#" * block
        block_nopr = "-" * (50 - block)

        pr_log(f"{bp_name[:20]:20}  |   ({count:6}) [{block_pr}{block_nopr}]")
