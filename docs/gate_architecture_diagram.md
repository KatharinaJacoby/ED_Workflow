# Gate Engine Architecture

## High-Level Design

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Layer    │    │  Assessment      │    │   Decision      │
│                 │    │  Engine          │    │   Layer         │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ • 16 ML Features│───▶│ Gate Categories: │───▶│ • Priority Score│
│ • Calculator    │    │                  │    │ • Next Actions  │
│   Results       │    │ 1. Transfer      │    │ • ETA Estimates │
│ • Patient       │    │    Readiness     │    │ • Status Badges │
│   Context       │    │ 2. Institutional │    │                 │
│ • Real-time     │    │    Timing        │    │                 │
│   Constraints   │    │ 3. Social        │    │                 │
│                 │    │    Discharge     │    │                 │
│                 │    │ 4. Clinical      │    │                 │
│                 │    │    Safety        │    │                 │
│                 │    │ 5. Resource      │    │                 │
│                 │    │    Constraints   │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Core Components

### 1. **Data Ingestion Layer**
- **Existing 16 ML Features**: Direct compatibility with your current pipeline
- **Clinical Calculator Integration**: HEART, qSOFA, troponin assessments
- **Contextual Data**: Patient demographics, institutional constraints
- **Real-time Constraints**: Time of day, ICU capacity, staff availability

### 2. **Assessment Engine (5 Gate Categories)**

#### Gate 1: Transfer Readiness (Medical Completion)
- **Input Sources**: `hat_Labor`, `Labor_ausstehend`, `hat_CT`, `CT_ausstehend`, `naechste_Aktion`
- **Assessment Logic**: 
  ```python
  def assess_transfer_readiness(features, calculators):
      score = 1.0
      if not features['hat_Labor']: score *= 0.3
      if features['Labor_ausstehend']: score *= 0.6
      if calculators['troponin_flag']: score *= 0.4
      # ... additional rules
      return GateStatus(score, blockers, actions, eta)
  ```

#### Gate 2: Institutional Timing
- **Input Sources**: Current time, `ICU_Kap`, weekend/holiday flags
- **Assessment Logic**: Time-based rules (4pm bed manager cutoff, night shift resistance)

#### Gate 3: Social Discharge  
- **Input Sources**: Age, insurance status, home support availability
- **Assessment Logic**: Age-based nursing home needs, GP access patterns

#### Gate 4: Clinical Safety
- **Input Sources**: `Leitsymptom`, `t_min`, calculator results
- **Assessment Logic**: Mandatory hold protocols, safety rails

#### Gate 5: Resource Constraints
- **Input Sources**: `ICU_Kap`, `Kap_veraltet`, queue lengths
- **Assessment Logic**: Capacity bottlenecks, resource availability

### 3. **Decision Layer**
- **Priority Scoring**: Weighted combination of gate readiness scores
- **Action Prioritization**: Most critical blocking gate determines next action
- **ETA Calculation**: Longest blocking gate determines timeline

## Implementation Steps

### Step 1: Define Gate Categories
```python
@dataclass
class GateStatus:
    category: str
    status: str  # "open", "blocked", "pending"
    readiness_score: float  # 0.0-1.0
    blockers: List[str]
    eta_minutes: Optional[int]
    actions_required: List[str]
```

### Step 2: Implement Assessment Logic
```python
class GateEngine:
    def assess_transfer_readiness(self, features, calculators):
        # Rule-based assessment logic
        pass
    
    def assess_institutional_timing(self, features, current_time):
        # Time-based constraint logic  
        pass
    
    # ... other gate assessments
```

### Step 3: Integration Points
```python
def compute_overall_readiness(self, features, calculators, context):
    gates = {
        'transfer': self.assess_transfer_readiness(features, calculators),
        'timing': self.assess_institutional_timing(features, datetime.now()),
        # ... other gates
    }
    
    overall_score = weighted_average(gates)
    priority = convert_to_priority(overall_score)
    next_action = prioritize_actions(gates)
    
    return {
        'priority': priority,
        'readiness_score': overall_score,
        'next_action': next_action,
        'gate_details': gates
    }
```

### Step 4: WorkflowState Integration
```python
def process_workflow_state(state: WorkflowState, calculators=None):
    features = state.feature_dict()  # Uses existing method
    # Add contextual data from state
    context = extract_patient_context(state)
    return gate_engine.compute_overall_readiness(features, calculators, context)
```

## Key Architectural Principles

1. **Deterministic Logic**: Rule-based assessment, not probabilistic
2. **Modular Design**: Each gate category is independently assessable
3. **Extensible**: Easy to add new gate categories or modify rules
4. **Integration-Friendly**: Works with existing data structures
5. **Actionable Output**: Every assessment produces specific next steps
6. **Real-time Aware**: Incorporates temporal and resource constraints