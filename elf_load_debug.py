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
from action import *
from main import *

## --- ELF DEBUG ---
@dataclass
class ElfLog:
    file_name: str
    addr: int
    prot: str
    size: int

    rid: int

@dataclass
class ElfLogHelper:
    rid: int
    entries: list[ElfLog] = field(default_factory=list)

    def update_log(self, name, addr, prot, size, index):
        while len(self.entries) <= index:
            self.entries.append(ElfLog(file_name="NULL", addr=0, prot="NULL", size=0, rid=self.rid))
        
        target = self.entries[index]
        
        if name is not None: 
            target.file_name = name
        if addr is not None: 
            target.addr = addr
        if prot is not None: 
            target.prot = prot
        if size is not None: 
            target.size = size

cargo_log: List[ElfLog] = []
cargo_log_helper: List[ElfLogHelper] = []

### --- ELF LOG ---
class ElfHandler():
    def __init__(self):
        self.count = {}

    def send_count(self, rid):
        if rid not in self.count:
            self.count[rid] = 0

            log = ElfLog(
                file_name = None,
                addr = None,
                prot = None,
                size = None,
                rid = rid
            )
            cargo_log.append(log)

            helper = ElfLogHelper(rid=rid)
            cargo_log_helper.append(helper)


        if elf_logger(rid, self.count[rid]):
            self.count[rid] += 1

    def entry(self, cbs):
        rid = cbs.rid
        self.send_count(rid)

def elf_logger(rid, idx):
    ret = False

    try:
        filep = get_var("filep")
        addr = get_var("addr")
        prot = get_var("prot")
        size = get_var("size")

        addr = int(addr)
        size = int(size)

        if size <= 0:
            return None

        prot = prot_to_str(prot)

        try:
            filen = filep['f_path']['dentry']['d_name']['name'].string()
        except:
            filen = "NULL"

        log = elf_find_log(rid)
        if log is None:
            return None

        log_helper = find_log_helper(rid)

        if log_helper:
            log_helper.update_log(filen, addr, prot, size, idx)
            ret = True
        else:
            pr_err(f"Helper not found: RID {rid}")

    except Exception as e:
        pr_err(f"Error in elf_logger {e}")

    return ret

def elf_find_log(rid):
    try:
        for log in cargo_log:
            if log.rid == rid:
                return log
    except:
        pr_debug(f"find_log: log {rid} is not exist")
        return None

def find_log_helper(rid):
    try:
        for i in cargo_log_helper:
            if i.rid == rid:
                return i
    except:
        pr_debug(f"find_log_helper: log helper {rid} is not exist")
        return None

def elf_map_log(rid):
    log = elf_find_log(rid)
    log_helper = find_log_helper(rid)

    if log is None:
        pr_debug("elf_map_log: None")
        return None

    for entry in log_helper.entries:

        summary = (f"CID: {entry.rid} | "
                   f"File: {entry.file_name[:15]:<15} | "
                   f"Addr: {hex(entry.addr):<12} | "
                   f"Prot: {entry.prot} | "
                   f"Size: {entry.size}")
        pr_log(summary)

    with open(log_file, "a") as f:
        for entry in log_helper.entries:

            line = (f"RID: {entry.rid} | File: {entry.file_name[:15]:<15} | "
                    f"Addr: 0x{entry.addr:016x} | Prot: {entry.prot} | Size: {entry.size}\n")
            f.write(line)
        
        f.write("- " * 50 + "\n")

    pr_log("- " * 50 + "\n")

def prot_to_str(p):     
    p = int(p)
    r = "r" if p & 1 else "-"
    w = "w" if p & 2 else "-"
    x = "x" if p & 4 else "-"
    return f"{r}{w}{x}"
