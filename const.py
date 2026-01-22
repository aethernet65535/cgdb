# --- Constant ---
## --- Flags ---
### --- Op Flags ---
SUB_NOROOT = 1 << 0
SUB_SHARED = 1 << 1
SUB_PRIVATE = 1 << 2
SUB_END = 1 << 3

FINISH_SHARED = 1 << 4
FINISH_PRIVATE = 1 << 5
FINISH_END = 1 << 6

### --- Type Flags ---
TYPE_ROOT = 1 << 0
TYPE_SUB = 1 << 1
TYPE_FINISH = 1 << 2
TYPE_END = 1 << 3

OP_FLAGS = (
    SUB_NOROOT |
    SUB_SHARED |
    SUB_PRIVATE |
    SUB_END |
    FINISH_SHARED |
    FINISH_PRIVATE |
    FINISH_END
)

TYPE_FLAGS = (
    TYPE_ROOT |
    TYPE_SUB |
    TYPE_FINISH |
    TYPE_END
)
