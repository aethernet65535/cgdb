import itertools
from dataclasses import dataclass, field
from typing import Callable, Optional

# --- Global ---
## --- Cargo ---
cargo_shared_root = []
cargo_shared_finish = []

cargo_bps = {}              # Key = bp_name
cargo_cbs = {}              # Key = bpid

framep_to_root_cbs = {}     # Key = framep

## --- Struct ---
@dataclass
class BreakpointStruct:
    bp_name: str

    flags: int = 0

    paper: Any = None
    action: Optional[Callable] = None

    root: list = field(default_factory=list)

@dataclass
class CallBreakStruct:
    archetype: BreakpointStruct
    framep: int     # Only for root
    bpid: int       # Breakpoint ID
    rid: int        # Root ID

@dataclass
class A4Paper:
    count: int
    rid: int

## --- Counter ---
bpid_generator = itertools.count(1)
rid_generator = itertools.count(1)
