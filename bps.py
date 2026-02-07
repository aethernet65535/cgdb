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
from action import *
from utils import *
from cbs import *

# --- Breakpoint Register ---
## --- Class ---
class GdbBp(gdb.Breakpoint):
    def __init__(self, bp):
        super().__init__(bp, gdb.BP_BREAKPOINT)
        self.bp = bp 

    def stop(self):
        bps = find_bps(self.bp)
        if not bps:
            pr_err("GdbBp: bps must existed")
            return False
    
        root = find_root(bps)
        if root is None:
            pr_debug("GdbBp: cbs not found")
            if not (bps.flags & TYPE_ROOT):
                return False

        cbs = register_cbs(self.bp, bps.flags)
        if cbs is None:
            return False

        if bps.action is not None:
            bps.action(cbs)

        return False

## --- Function ---
def gdb_bp(sub_bp, root_bp, flags, paper, action):
    global cargo_bps
    should_add = 0
    
    if not sub_bp:
        pr_err("gdb_bp: sub function not found")

    if root_bp:
        should_add = 1

    if sub_bp not in cargo_bps or cargo_bps.get(sub_bp) is None:
        bps = BreakpointStruct(
            bp_name = sub_bp,
            flags = flags,
            paper = paper,
            action = action
        )
        if should_add:
            bps.root.append(root_bp)
        cargo_bps[sub_bp] = bps
        GdbBp(sub_bp)
    else:
        if should_add:
            cargo_bps[sub_bp].root.append(root_bp)

    if should_add:
        gdb_bp(root_bp, None, TYPE_ROOT, None, None)

def register_bps(other_bp, root_bp, flags, paper, action):
    tmp = flags_check(flags)
    if tmp is None:
        pr_err("register_bps: flags_check() is None")
        return None

    return gdb_bp(other_bp, root_bp, flags, paper, action)
