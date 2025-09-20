from dataclasses import dataclass, field

@dataclass
class QAschema:
    debug: str = ""          # debug info
    fr_assigned: list[str] = field(default_factory=list) # list of FR ids assigned
    global_text: str = ""         # full requirements doc
    fr_id: str = ""               # current FR being worked on
    fr_text: str = ""             # text for this FR
    step: int = 1                 # which step (1–8)
    content: str = ""             # last output