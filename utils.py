import itertools
import gdb
import os
import sys
import itertools
import time
import threading

from dataclasses import dataclass, field
from typing import Callable, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from config import *
from color_debug import *
from global_var import *
from const import *

# ====================
# === --- CODE --- ===
# ====================
#
# --- General Function ---
## --- BPS ---
def find_bps(bp_name):
    bps = cargo_bps.get(bp_name)

    if bps is None:
        return -1
    else:
        return bps

## --- xID ---
def next_bpid():
    return next(bpid_generator)

def next_rid():
    return next(rid_generator)

## --- Check ---
def flags_check(f):
    if f is None:
        f = 0

    if f & TYPE_FINISH:
        if f & (TYPE_ROOT | TYPE_SUB):
            return None

    if f & TYPE_ROOT and f & OTHERS_SHARED:
        return None

    if f & ~STATE_FLAGS:
        return None

    return 0

## --- Walk ---
def _get_frame_pointer(curr_frame):
    ret = None

    if ARCH == "x86":
        ret = int(curr_frame.read_register("rbp"))

    if ret is None:
        pr_err("get_frame_pointer: no matched architecture")

    return ret

def get_frame_pointer():
    frame = gdb.selected_frame()
    
    return _get_frame_pointer(frame)

def find_matched_cbs(bps, cbs):
    if cbs is None:
        return False

    cbs_name = cbs.archetype.bp_name

    for bps_name in bps.root:
        if cbs_name == bps_name:
            return True

    return False

def find_archetype(bp_name):
    if not bp_name:
        return None

    return cargo_bps.get(bp_name)

def find_root(bps):
    global ARCH

    frame = gdb.selected_frame()
    cbs = None

    if ARCH == "x86":
        cbs = x86_find_root(frame, 0, bps)
        if not cbs:
            return None

    if cbs is None:
        pr_err("find_root: matched architecture not found")
        return None

    return cbs 

def x86_find_root(curr_frame, depth, bps):
    while curr_frame and depth < 100:
        framep = _get_frame_pointer(curr_frame)
        
        if framep:
            cbs = framep_to_root_cbs.get(framep)
            if find_matched_cbs(bps, cbs):
                return cbs
        
        curr_frame = curr_frame.older()
        depth += 1

    return None

def get_var(var):
    try:
        ret = gdb.parse_and_eval(var)
        if ret.is_optimized_out:
            ret = "VAR_OPTIMIZED"
    except gdb.error as e:
        ret = "VAR_ERROR"

    return ret

def get_addr(var):
    try:
        ret = gdb.parse_and_eval(var)
        addr = ret.address

        if addr is None:
            ret = "ADDR_REGISTER"
    except gdb.error as e:
        ret = "ADDR_ERROR"

    return ret
