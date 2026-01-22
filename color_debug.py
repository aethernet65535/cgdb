from config import *

# --- Color Debug ---
C_RED    = "\033[91m"
C_GREEN  = "\033[92m"
C_YELLOW = "\033[93m"
C_BLUE   = "\033[94m"
C_MAGENTA= "\033[95m"
C_CYAN   = "\033[96m"
C_END    = "\033[0m"

## --- Color ---
def print_red(text):
    print(f"{C_RED}{text}{C_END}")

def print_green(text):
    print(f"{C_GREEN}{text}{C_END}")

def print_blue(text):
    print(f"{C_BLUE}{text}{C_END}")

def pr_err(text):
    if CONFIG_ERR:
        print_red(f"[ERROR] {text}")

def pr_debug(text):
    if CONFIG_DEBUG:
        print_green(f"[DEBUG] {text}")

def pr_log(text):
    if CONFIG_LOG:
        print_blue(f"[LOG] {text}")
