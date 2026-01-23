import os
import sys

# ====================
# === --- USER --- ===
# ====================
#
# === Config ===
linux_path = os.path.expandvars("$LINUX_MAINLINE")
log_file = os.path.join(linux_path, "debug/log/gdb_break.log")
log_dir = os.path.dirname(log_file)
vmlinux_bin = os.path.join(linux_path, "build/qemu/vmlinux")

# === Fix "No module named linux" ===
gdb_scripts_path = os.path.join(linux_path, "scripts/gdb")
if gdb_scripts_path not in sys.path:
    sys.path.append(gdb_scripts_path)

# === ARCH ===
ARCH = "x86"

# === DEBUG ===
CONFIG_ERR = 1
CONFIG_DEBUG = 0
CONFIG_LOG = 0
