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


def test_fn():
    print("TEST_FN: CALLED")


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

    if f & (SUB_END | FINISH_END):
        return -1

    if f & ~OP_FLAGS:
        return -1

    return 0

def type_check(t):
    if t is None:
        t = 0

    if t & (TYPE_END):
        return -1

    if t & TYPE_FINISH and t != TYPE_FINISH:
        return -1

    if t & ~TYPE_FLAGS:
        return -1

    return 0

## --- Walk ---
def _get_frame_pointer(curr_frame):
    ret = -1

    if ARCH == "x86":
        ret = int(curr_frame.read_register("rbp"))

    if ret == -1:
        pr_err("get_frame_pointer: no matched architecture")

    return ret

def get_frame_pointer():
    frame = gdb.selected_frame()
    
    return _get_frame_pointer(frame)

def find_matched_cbs(bps, cbs):
    if cbs is None:
        return -1

    cbs_name = cbs.archetype.bp_name

    for bps_name in bps.private_root:
        if cbs_name == bps_name:
            return 0

    return -1

def find_archetype(bp_name):
    if not bp_name:
        return None

    return cargo_bps.get(bp_name)

def find_root(bps):
    global ARCH

    frame = gdb.selected_frame()
    ret = -1

    if ARCH == "x86":
        ret = x86_find_root(frame, 0, bps)
        if ret is None:
            return

    if ret == -1:
        pr_err("find_root: matched architecture not found")
        return

def x86_find_root(curr_frame, depth, bps):
    while curr_frame and depth < 100:
        framep = _get_frame_pointer(curr_frame)
        
        if framep != -1:
            cbs = framep_to_root_cbs.get(framep)
            if find_matched_cbs(bps, cbs) < 0:
                pass
            else:
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
def create_breakpoint_call(bp_name, flags, t_type, void, action):
    global cargo_cbs
    global framep_to_root_cbs

    bpid = next_bpid()

    archetype = find_archetype(bp_name)
    if archetype is None:
        pr_debug("archetype not found")
        return None

    root_call = find_root(archetype)
    if root_call is None:
        pr_debug("root not found")
        
        if not (t_type & TYPE_ROOT):
            return None

    # `t_type` here means "Where did it come from",
    # not what the `t_type` corresponding to the
    # archetype are.
    if not (t_type & TYPE_ROOT):
        if root_call.rid:
            rid = root_call.rid
        else:
            pr_err("_create_breakpoint_struct: no rid found")

        framep = 0
    else: # is root
        framep = get_frame_pointer()
        rid = next_rid()

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
        return -1

    # Will use it for find root's framep,
    # so don't give cbs if framep is 0.
    if t_type & TYPE_ROOT and framep != 0:
        framep_to_root_cbs[framep] = cbs

    pr_debug(f"BPID: {bpid} | name: {bp_name} | CREATE_SUCCESS")
    return bpid

# Note:
# This will be called frequently during runtime.
# So don't call it for a single initialzalation, such as
# gdb.Breakpoint.
def register_breakpoint_call(bp_name, flags, cbs_type, void, action):
    if flags_check(flags) < 0:
        pr_err("_register_breakpoint: illegal flags")
        return -1
    if type_check(cbs_type) < 0:
        pr_err("_register_breakpoint: illegal type")
        return -1

    bpid = create_breakpoint_call(bp_name, flags, cbs_type, void, action)
    if bpid is None:
        pr_err("_register_breakpoint: create failed")
        return -1
    return bpid



# --- Breakpoint Register ---
## --- Class ---
class GdbRoot(gdb.Breakpoint):
    def __init__(self, root_bp):
        super().__init__(root_bp, gdb.BP_BREAKPOINT)
        self.root_bp = root_bp

    def stop(self):
        type = TYPE_ROOT

        # Ensure `root_bp` is existed.
        bps = find_bps(root_bp)
        if not bps:
            pr_err("GdbRoot: bps must existed")
            return False

        cbs = find_root(bps)
        if cbs is None:
            pr_debug("GdbRoot: cbs not found")
        else:
            pr_debug(f"{cbs.archetype.bp_name}")

        bpid = register_breakpoint_call(root_bp, None, TYPE_ROOT, None, None)
        if bpid is None:
            return False

        if bps.action is not None:
            bps.action()

        return False

## --- Function ---
def gdb_root(root_bp, root_bp2, flags, void, action):
    global cargo_bps
    should_add = 1

    if not root_bp:
        pr_err("gdb_root: root function not found")
        return -1

    if not root_bp2:
        should_add = 0

    if root_bp not in cargo_bps or cargo.get(root_bp) is None:
        bps = BreakpointStruct(
            bp_name = root_bp,
            flags = flags,
            bps_type = TYPE_ROOT,
            void = void,
            action = action
        )
        if should_add:
            bps.private_root.append(root_bp2)
        pr_debug(f"early bps: {type(bps)}")
        cargo_bps[root_bp] = bps
        GdbRoot(root_bp)
    else:
        if should_add:
            cargo_bps[root_bp].private_root.append(root_bp2)

# This will only called a single time, when the script just run.
#
# This function will init the breakpoint, and the 'gdb_xxx()' function
# will call the 'register_breakpoint()' each time the breakpoint
# stopped.
def register_bps(other_bp, root_bp, flags, bps_type, void, action):

    # The 'other_bp' may be kinda hard, because we may also need to register
    # the for the root_bp, so 'GdbFinish()' and 'GdbSub()' may not easy as
    # 'GdbRoot()'.
    #
    # I'm not sure about it yet, just noted :>

    if bps_type == TYPE_FINISH:
        return gdb_finish(other_bp, root_bp, flags, action)

    if bps_type == TYPE_SUB:
        return gdb_sub(other_bp, root_bp, flags, void, action)

    if bps_type == TYPE_ROOT:
        return gdb_root(other_bp, root_bp, flags, void, action)

def root_register(root):
    return register_bps(root, None, None, TYPE_ROOT, None, None)



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
    # root_register(root_bp)
    register_bps(root_bp, None, None, TYPE_ROOT, None, test_fn)
    # register_bp(bp1, bp2, flags, type, paper, action)

def main():
    gdb_init()
    register_config()
    gdb_start()

if __name__ == "__main__":
    main()
