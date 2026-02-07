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
from bps import *

from elf_load_debug import *

### --- Setup ---
class GdbTrigger(gdb.Breakpoint):
    def __init__(self, bp):
        super().__init__(bp, gdb.BP_BREAKPOINT)
        self.init = 0

    def stop(self):
        if not self.init:
            register_config()
            self.init = 1

        return False

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
    print("Breakpoint settings...")

    r_paper = A4Paper(count = 0, rid = 0)
    f_paper = A4Paper(count = 0, rid = 0)

    root_bp = "load_elf_binary"
    sub_bp1 = "elf_map"

    eh = ElfHandler()

    register_bps(root_bp, None, TYPE_ROOT, r_paper, action_count)
    register_bps("debug_gdb_fn_finish", root_bp, \
                 TYPE_FINISH, f_paper, action_box)

    register_bps(sub_bp1, root_bp, TYPE_SUB, None, eh.entry)

    print("Breakpoint done!")

def main():
    gdb_init()
    GdbTrigger("do_execve")
    gdb_start()

if __name__ == "__main__":
    main()
