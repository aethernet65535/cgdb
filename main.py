import gdb
import os
import sys
import itertools

from dataclasses import dataclass, field
from typing import Callable

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from config import *
from color_debug import *
from global_var import *
from const import *



# ======================
# === --- ACTION --- ===
# ======================
#
# --- Utils ---
def action_finish_free(cbs):
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

## --- Toys ---
#
# Needed:
# - paper with `count` field.
def action_all_count(cbs):

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
    count = action_all_count(cbs)
    if count is None:
        return None
    
    rid = cbs.archetype.paper.rid
    if rid != cbs.rid:
        rid = cbs.rid
    else:
        pr_err("WHATTTTTTT")

    name = cbs.archetype.bp_name

    pr_log("="*80)
    pr_log(f"{name}: count = {count}")
    pr_log("="*80)


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



# ====================
# === --- MAIN --- ===
# ====================
#
def gdb_init():
    gdb.execute("set python print-stack full")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    gdb.execute(f"file {vmlinux_bin}")

    with open(log_file, "w") as f:
            f.write("====================\n")
            f.write("GDB PRO DEBUG START\n")
            f.write("====================\n")
    try:
        gdb.execute("target remote:1234")
    except gdb.error as e:
        pr_debug(f"Connection failed: {e}")

def gdb_start():
    print("Starting execution...")
    gdb.execute("continue")

def register_config():
    aa_paper = A4Paper(count = 0, rid = 0)
    a1_paper = A4Paper(count = 0, rid = 0)
    a2_paper = A4Paper(count = 0, rid = 0)

    root_bp = "do_pte_missing"
    sbp = "do_anonymous_page"
    sbp1 = "do_fault"

    register_bps(root_bp, None, TYPE_ROOT, aa_paper, action_name_count)
    register_bps(sbp, root_bp, TYPE_SUB, a1_paper, action_name_count)
    register_bps(sbp1, root_bp, TYPE_SUB, a2_paper, action_name_count)

    register_bps("debug_gdb_fn_finish", root_bp, \
                 TYPE_FINISH, None, action_finish_free)

def main():
    gdb_init()
    register_config()
    # gdb_start()

if __name__ == "__main__":
    main()
