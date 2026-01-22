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
def test_fn(cbs):
    bp_name = cbs.archetype.bp_name

    pr_log(f"TEST_FN: archetype = {bp_name}")

    root = find_root(cbs.archetype)
    if root:
        pr_log(f"TEST_FN: root = {root.archetype.bp_name}")
        pr_log(f"TEST_FN: rid = {root.rid}")
        pr_log(f"TEST_FN: bpid = {root.bpid}")
    else:
        pr_log("TEST_FN: root not found")

    with open(log_file, "a") as f:
        f.write("TEST_FN: CALLED\n")
        f.write(f"TEST_FN: archetype = {bp_name}\n")
        if root:
            f.write(f"TEST_FN: root = {root.archetype.bp_name}\n")
            f.write(f"TEST_FN: rid = {root.rid}")
            f.write(f"TEST_FN: bpid = {root.bpid}")
        else:
            f.write("TEST_FN: root not found\n")

def clear_fn(cbs):
    global cargo_cbs, framep_to_root_cbs

    pr_log("CLEAR_FN: CALLED")

    curr_rid = cbs.rid
    root = find_root(cbs.archetype)
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

    pr_log("ALL DONE!!")
    pr_log("-" *80)


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

    if f & TYPE_FINISH and f != TYPE_FINISH:
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
# When `other` triggers a breakpoint, it will try to find the
# corresponding `root's CBS` in older frame.
#
# Once found, it will triggers `register_breakpoint_call()` and
# calls this function.
#
# Simply put, any `other` that reaches here, will have a
# chance to trigger an `action` (if it have).
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

# Note:
# This will be called frequently during runtime.
# So don't call it for a single initialzalation, such as
# gdb.Breakpoint.
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
class GdbRoot(gdb.Breakpoint):
    def __init__(self, root_bp):
        super().__init__(root_bp, gdb.BP_BREAKPOINT)
        self.root_bp = root_bp

    def stop(self):
        # Ensure `root_bp` is existed.
        bps = find_bps(self.root_bp)
        if not bps:
            pr_err("GdbRoot: bps must existed")
            return False

        root = find_root(bps)
        if root is None:
            pr_debug("GdbRoot: cbs not found")

        cbs = register_cbs(self.root_bp, bps.flags)
        if cbs is None:
            return False

        if bps.action is not None:
            bps.action(cbs)

        return False

class GdbFinish(gdb.Breakpoint):
    def __init__(self, finish_bp):
        super().__init__(finish_bp, gdb.BP_BREAKPOINT)
        self.finish_bp = finish_bp

    def stop(self):
        bps = find_bps(self.finish_bp)
        if not bps:
            pr_err("GdbFinish: bps must existed")
            return False
    
        root = find_root(bps)
        if root is None:
            pr_err("GdbFinish: cbs not found")
            return False

        cbs = register_cbs(self.finish_bp, bps.flags)
        if cbs is None:
            return False

        if bps.action is not None:
            bps.action(cbs)

        return False

## --- Function ---
def gdb_root(root_bp, root_bp2, flags, void, action):
    global cargo_bps
    should_add = 0

    if not root_bp:
        pr_err("gdb_root: root function not found")

    if root_bp2:
        should_add = 1

    if root_bp not in cargo_bps or cargo_bps.get(root_bp) is None:
        bps = BreakpointStruct(
            bp_name = root_bp,
            flags = flags,
            void = void,
            action = action
        )
        if should_add:
            bps.root.append(root_bp2)
        cargo_bps[root_bp] = bps
        GdbRoot(root_bp)
    else:
        if should_add:
            cargo_bps[root_bp].root.append(root_bp2)

    if should_add:
        gdb_root(root_bp2, None, TYPE_ROOT, None, None)

def gdb_finish(finish_bp, root_bp, flags, void, action):
    global cargo_bps
    should_add = 0

    if root_bp:
        should_add = 1

    if not finish_bp:
        pr_err("gdb_finish: finish function not found")

    if finish_bp not in cargo_bps or cargo_bps.get(finish_bp) is None:
        bps = BreakpointStruct(
            bp_name = finish_bp,
            flags = flags,
            void = void,
            action = action
        )
        if should_add:
            bps.root.append(root_bp)
        cargo_bps[finish_bp] = bps
        GdbFinish(finish_bp)
    else:
        if should_add:
            cargo_bps[finish_bp].root.append(root_bp)

    if should_add:
        gdb_root(root_bp, None, TYPE_ROOT, None, None)

# This will only called a single time, when the script just run.
#
# This function will init the breakpoint, and the 'gdb_xxx()' function
# will call the 'register_breakpoint()' each time the breakpoint
# stopped.
def register_bps(other_bp, root_bp, flags, void, action):

    # The 'other_bp' may be kinda hard, because we may also need to register
    # the for the root_bp, so 'GdbFinish()' and 'GdbSub()' may not easy as
    # 'GdbRoot()'.
    #
    # I'm not sure about it yet, just noted :>

    tmp = flags_check(flags)
    if tmp is None:
        pr_err("register_bps: flags_check() is None")
        return None

    if flags & TYPE_FINISH:
        return gdb_finish(other_bp, root_bp, flags, void, action)

    if flags & TYPE_SUB:
        return gdb_sub(other_bp, root_bp, flags, void, action)

    if flags & TYPE_ROOT:
        return gdb_root(other_bp, root_bp, flags, void, action)

def root_register(root):
    return register_bps(root, None, TYPE_ROOT, None, None)



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
    register_bps(root_bp, root_bp2, TYPE_ROOT, None, test_fn)
    register_bps(finish_bp, root_bp2, TYPE_FINISH, None, clear_fn)

def main():
    gdb_init()
    register_config()
    gdb_start()

if __name__ == "__main__":
    main()
