@dataclass
class WorkflowState:
    encounter_id: Optional[str] = None
    patient_id: Optional[str] = None
    pending_orders: set = field(default_factory=set)
    completed_studies: set = field(default_factory=set)
    active_consults: set = field(default_factory=set)
    last_vitals_ts: Optional[pd.Timestamp] = None
    chest_pain: bool = False
    breathing_problem: bool = False
    trauma: bool = False
    spo2: Optional[float] = None
    # context
    backlog_ct: int = 0
    backlog_lab: int = 0
    backlog_ecg: int = 0
    hour: int = 12
    role: str = "nurse"
    # timing
    now_ts: Optional[pd.Timestamp] = None
    event_times: Dict[str, pd.Timestamp] = field(default_factory=dict)

def update_state_from_event(state: WorkflowState, row: pd.Series):
    