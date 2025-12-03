import json, time, uuid
from dataclasses import dataclass, asdict

BASE = "lab/cnp" 

def now_s() -> float:
    return time.time()

def new_job_id() -> str:
    return uuid.uuid4().hex[:12]

def jdump(obj) -> str:
    return json.dumps(obj, separators=(",", ":"))

def jload(b: bytes):
    return json.loads(b.decode())

@dataclass
class CfP:
    job_id: str
    job_type: str
    deadline_s: float     # seconds
    issued_at: float      # timestamp epoch

    def to_msg(self):
        return jdump(asdict(self))

@dataclass
class Proposal:
    job_id: str
    job_type: str
    machine_id: str
    eta_s: float          # promised time (seconds)
    at: float

    def to_msg(self):
        return jdump(asdict(self))

@dataclass
class Accept:
    job_id: str
    job_type: str

    def to_msg(self):
        return jdump(asdict(self))

@dataclass
class Done:
    job_id: str
    job_type: str
    machine_id: str
    started_at: float
    finished_at: float

    def to_msg(self):
        return jdump(asdict(self))


def t_cfp(job_type: str) -> str:
    # Broadcast
    return f"{BASE}/cfp/{job_type}"

def t_proposals() -> str:
    return f"{BASE}/proposals"

def t_accept(machine_id: str) -> str:
    return f"{BASE}/accept/{machine_id}"

def t_done() -> str:
    return f"{BASE}/done"
