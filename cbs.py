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
from utils import *

# --- Breakpoint Run-Time Create ---
def create_cbs(bp_name, flags):
    global cargo_cbs
    global framep_to_root_cbs

    bpid = next_bpid()

    archetype = find_archetype(bp_name)
    if archetype is None:
        pr_err("archetype not found")
        return None

    root_call = find_root(archetype)
    if root_call is None:
        pr_debug("root not found")
        
        if not (flags & TYPE_ROOT):
            return None

    if (flags & TYPE_ROOT):
        framep = get_frame_pointer()
        rid = next_rid()
    else:
        if root_call.rid:
            rid = root_call.rid
        else:
            pr_err("create_cbs: no rid found")
        
        framep = 0

    cbs = CallBreakStruct(
        archetype = archetype,
        framep = framep,
        bpid = bpid,
        rid = rid
    )
    if cargo_cbs.get(bpid) is None:
        cargo_cbs[bpid] = cbs
    else:
        pr_err("cargo_cbs: cargo_cbs[bpid] is not None")
        return None

    # Will use it for find root's framep,
    # so don't give cbs if framep is 0.
    if flags & TYPE_ROOT and framep != 0:
        framep_to_root_cbs[framep] = cbs

    pr_debug(f"BPID: {bpid} | name: {bp_name} | CREATE_SUCCESS")
    return cbs 

def register_cbs(bp_name, flags):
    if flags_check(flags) is None:
        pr_err("_register_breakpoint: illegal flags")
        return None

    cbs = create_cbs(bp_name, flags)
    if cbs is None:
        pr_err("_register_breakpoint: create failed")
        return None
    return cbs 
