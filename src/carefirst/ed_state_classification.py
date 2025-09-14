# === ED State Classification System ===
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

@dataclass
class EDStateThresholds:
    """Configuration for ED state classification"""
    high_volume_census: float = 40.0
    high_volume_wait_time: float = 60.0  # minutes
    resource_constrained_staff_ratio: float = 0.12
    resource_constrained_icu_occupancy: float = 0.90
    critical_surge_census: float = 55.0
    critical_surge_wait_time: float = 120.0
    night_shift_start: int = 20
    night_shift_end: int = 6
    flu_season_months: List[int] = None
    
    def __post_init__(self):
        if self.flu_season_months is None:
            self.flu_season_months = [11, 12, 1, 2, 3]  # Nov-Mar

class EDStateClassifier:
    """Classifies current ED operational state"""
    
    def __init__(self, thresholds: EDStateThresholds = None):
        self.thresholds = thresholds or EDStateThresholds()
    
    def classify_state(self, operational_context: Dict[str, float]) -> str:
        """Classify ED state based on operational context"""
        
        # Extract key metrics
        census = operational_context.get("current_census", 0)
        wait_time = operational_context.get("avg_wait_time_min", 0)
        staff_ratio = operational_context.get("staff_patient_ratio", 1.0)
        icu_occupancy = operational_context.get("icu_occupancy", 0.0)
        hour = operational_context.get("hour_of_day", 12)
        month = operational_context.get("month", 6)
        
        # Priority order matters - most severe states first
        
        # Critical Surge (highest priority)
        if (census >= self.thresholds.critical_surge_census or 
            wait_time >= self.thresholds.critical_surge_wait_time):
            return "Critical_Surge"
        
        # High Volume
        if (census >= self.thresholds.high_volume_census or 
            wait_time >= self.thresholds.high_volume_wait_time):
            return "High_Volume"
        
        # Resource Constrained
        if (staff_ratio <= self.thresholds.resource_constrained_staff_ratio or 
            icu_occupancy >= self.thresholds.resource_constrained_icu_occupancy):
            return "Resource_Constrained"
        
        # Night Shift
        if (hour >= self.thresholds.night_shift_start or 
            hour <= self.thresholds.night_shift_end):
            return "Night_Shift"
        
        # Flu Season (modifier to other states)
        if month in self.thresholds.flu_season_months:
            return "Flu_Season"
        
        # Default
        return "Normal_Flow"

class StateCoordinationStrategy:
    """Defines coordination strategies for each ED state"""
    
    @staticmethod
    def get_strategy_config(ed_state: str, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Return modified config for given ED state"""
        
        config = dict(base_config)  # Copy base config
        
        if ed_state == "Critical_Surge":
            # Emergency protocols - very aggressive
            config.update({
                "TH_ICU_CAP_OK": 0.05,  # Much lower threshold
                "HANDOFF_DEADLINE_MIN": 15,  # Faster handoffs
                "DEFER_NON_URGENT": True,
                "ALERT_ESCALATION_MIN": 2,  # Immediate escalation
                "DISCHARGE_PREP_ADVANCE_MIN": 60  # Earlier discharge prep
            })
        
        elif ed_state == "High_Volume":
            # Tighter timing, more aggressive flow
            config.update({
                "TH_ICU_CAP_OK": 0.10,
                "HANDOFF_DEADLINE_MIN": 30,
                "DISCHARGE_PREP_ADVANCE_MIN": 45,
                "TRIAGE_EXPEDITE_THRESHOLD": 0.3,  # Lower bar for fast-track
                "LAB_PRIORITY_BOOST": True
            })
        
        elif ed_state == "Resource_Constrained":
            # Prioritize high-turnover cases
            config.update({
                "PRIORITIZE_HIGH_TURNOVER": True,
                "DEFER_ELECTIVE_WORKUP": True,
                "CONSOLIDATE_ROUNDS": True,
                "TH_ICU_CAP_OK": 0.08,  # More sensitive to capacity
                "ALERT_THRESHOLD_MIN": 3  # Reduce alert fatigue
            })
        
        elif ed_state == "Night_Shift":
            # Adjust for reduced specialist availability
            config.update({
                "SPECIALIST_AVAILABILITY": 0.3,  # Reduced availability
                "DEFER_SPECIALIST_CONSULTS": True,
                "MORNING_HANDOFF_PREP": True,
                "TH_ICU_CAP_OK": 0.20,  # Less aggressive at night
                "ALERT_THRESHOLD_MIN": 8  # Higher threshold at night
            })
        
        elif ed_state == "Flu_Season":
            # Anticipate isolation needs
            config.update({
                "ISOLATION_BED_RESERVE": 0.2,
                "RESPIRATORY_WORKUP_PRIORITY": True,
                "DISCHARGE_CRITERIA_STRICT": True,
                "INFECTION_CONTROL_ALERTS": True
            })
        
        # Normal_Flow uses base config unchanged
        
        return config

def collect_ed_operational_context() -> Dict[str, float]:
    """Collect current ED operational metrics"""
    now = datetime.now(timezone.utc)
    
    # In production, these would come from EMR/monitoring systems
    # For research, use realistic synthetic values or manual inputs
    
    context = {
        # Temporal
        "hour_of_day": float(now.hour),
        "day_of_week": float(now.weekday()),
        "month": float(now.month),
        
        # Current state (mock realistic values)
        "current_census": np.random.normal(35, 10),  # Patients in ED
        "avg_wait_time_min": np.random.normal(45, 20),  # Avg wait time
        "staff_patient_ratio": np.random.normal(0.15, 0.03),  # Nurse:patient
        "icu_occupancy": np.random.normal(0.8, 0.1),  # ICU beds occupied
        
        # Leading indicators
        "ems_arrivals_2h": np.random.poisson(8),  # EMS volume
        "admission_rate": np.random.normal(0.25, 0.05),  # % admitted
        "avg_los_current": np.random.normal(4.5, 1.0),  # Hours
    }
    
    # Ensure realistic bounds
    context["current_census"] = max(15, min(60, context["current_census"]))
    context["avg_wait_time_min"] = max(10, min(180, context["avg_wait_time_min"]))
    context["staff_patient_ratio"] = max(0.08, min(0.25, context["staff_patient_ratio"]))
    context["icu_occupancy"] = max(0.5, min(1.0, context["icu_occupancy"]))
    
    return context

# Integration with existing gate engine
def state_aware_gate_engine(fd: Dict[str, Any], CONFIG: Dict[str, Any]) -> Dict[str, Any]:
    """Gate engine with ED state-aware coordination strategies"""
    
    # Check if state-aware mode is enabled
    if not CONFIG.get("USE_STATE_AWARENESS", False):
        return gate_engine(fd, CONFIG)
    
    # Collect operational context and classify state
    op_context = collect_ed_operational_context()
    classifier = EDStateClassifier()
    current_state = classifier.classify_state(op_context)
    
    # Get strategy-specific configuration
    strategy_config = StateCoordinationStrategy.get_strategy_config(current_state, CONFIG)
    
    # Run gate engine with adapted configuration
    result = gate_engine(fd, strategy_config)
    
    # Add state information to result
    result["ed_state"] = current_state
    result["operational_context"] = op_context
    result["strategy_adaptations"] = {
        k: strategy_config[k] for k in strategy_config 
        if k not in CONFIG or CONFIG[k] != strategy_config[k]
    }
    
    # Log for research tracking
    try:
        _append_event({
            "type": "ed_state_coordination",
            "ed_state": current_state,
            "operational_context": op_context,
            "patient_gates": result["gates"],
            "adaptations": result["strategy_adaptations"]
        })
    except:
        pass
    
    return result

# Evaluation framework for measuring state classification effectiveness
class StateEffectivenessEvaluator:
    """Evaluate effectiveness of state-based coordination strategies"""
    
    def __init__(self):
        self.state_outcomes = {state: [] for state in [
            "Normal_Flow", "High_Volume", "Resource_Constrained", 
            "Critical_Surge", "Night_Shift", "Flu_Season"
        ]}
    
    def record_outcome(self, ed_state: str, predicted_state: str, 
                      los_actual: float, patient_id: str = None):
        """Record outcome for a patient under given state"""
        
        self.state_outcomes[ed_state].append({
            "predicted_state": predicted_state,
            "actual_los": los_actual,
            "correct_classification": ed_state == predicted_state,
            "patient_id": patient_id,
            "timestamp": datetime.now(timezone.utc)
        })
    
    def analyze_los_by_state(self) -> pd.DataFrame:
        """Analyze LOS outcomes by ED state"""
        
        results = []
        for state, outcomes in self.state_outcomes.items():
            if not outcomes:
                continue
                
            df = pd.DataFrame(outcomes)
            correct_class = df[df["correct_classification"] == True]
            incorrect_class = df[df["correct_classification"] == False]
            
            results.append({
                "ed_state": state,
                "total_patients": len(df),
                "correct_classifications": len(correct_class),
                "classification_accuracy": len(correct_class) / len(df) if len(df) > 0 else 0,
                "avg_los_correct": correct_class["actual_los"].mean() if len(correct_class) > 0 else None,
                "avg_los_incorrect": incorrect_class["actual_los"].mean() if len(incorrect_class) > 0 else None,
                "los_improvement": (incorrect_class["actual_los"].mean() - correct_class["actual_los"].mean()) 
                                 if len(correct_class) > 0 and len(incorrect_class) > 0 else None
            })
        
        return pd.DataFrame(results)
    
    def simulate_evaluation(self, num_patients: int = 1000) -> pd.DataFrame:
        """Simulate evaluation with synthetic patients"""
        
        np.random.seed(42)  # Reproducible results
        
        # Generate synthetic patient scenarios
        for i in range(num_patients):
            # Simulate operational context
            op_context = collect_ed_operational_context()
            
            # True state (ground truth)
            classifier = EDStateClassifier()
            true_state = classifier.classify_state(op_context)
            
            # Simulate prediction (with some error)
            predicted_state = true_state if np.random.random() > 0.2 else np.random.choice([
                "Normal_Flow", "High_Volume", "Resource_Constrained", 
                "Critical_Surge", "Night_Shift", "Flu_Season"
            ])
            
            # Simulate LOS outcome (better outcomes when correctly classified)
            base_los = {"Normal_Flow": 4.0, "High_Volume": 5.5, "Resource_Constrained": 6.0,
                       "Critical_Surge": 7.0, "Night_Shift": 4.5, "Flu_Season": 5.0}[true_state]
            
            if true_state == predicted_state:
                # Correct classification -> better LOS
                los_actual = np.random.normal(base_los * 0.85, base_los * 0.2)
            else:
                # Incorrect classification -> worse LOS
                los_actual = np.random.normal(base_los * 1.15, base_los * 0.25)
            
            los_actual = max(1.0, los_actual)  # Minimum 1 hour LOS
            
            self.record_outcome(true_state, predicted_state, los_actual, f"sim_{i}")
        
        return self.analyze_los_by_state()

# Research UI extension
def add_state_awareness_ui():
    """Add ED state awareness controls to existing UI"""
    
    if not CONFIG.get("RUN_UI"):
        return
        
    try:
        import ipywidgets as W
        
        # State awareness toggle
        state_toggle = W.Checkbox(
            description="Enable ED State Awareness",
            value=CONFIG.get("USE_STATE_AWARENESS", False)
        )
        
        # Current state display
        state_btn = W.Button(description="Check Current ED State")
        state_out = W.Output()
        
        def show_current_state(_):
            with state_out:
                state_out.clear_output()
                context = collect_ed_operational_context()
                classifier = EDStateClassifier()
                current_state = classifier.classify_state(context)
                
                print(f"Current ED State: {current_state}")
                print("\nOperational Context:")
                for k, v in context.items():
                    print(f"  {k}: {v:.2f}")
                
                strategy_config = StateCoordinationStrategy.get_strategy_config(current_state, CONFIG)
                adaptations = {k: v for k, v in strategy_config.items() 
                             if k not in CONFIG or CONFIG[k] != v}
                
                if adaptations:
                    print(f"\nStrategy Adaptations for {current_state}:")
                    for k, v in adaptations.items():
                        print(f"  {k}: {v}")
                else:
                    print(f"\nNo adaptations needed for {current_state}")
        
        state_btn.on_click(show_current_state)
        
        # Evaluation simulation
        eval_btn = W.Button(description="Simulate LOS Evaluation")
        eval_out = W.Output()
        
        def run_evaluation(_):
            with eval_out:
                eval_out.clear_output()
                print("Running LOS evaluation simulation...")
                evaluator = StateEffectivenessEvaluator()
                results = evaluator.simulate_evaluation(500)
                display(results)
                
                # Summary statistics
                avg_improvement = results["los_improvement"].mean()
                accuracy = results["classification_accuracy"].mean()
                print(f"\nOverall Results:")
                print(f"Average Classification Accuracy: {accuracy:.2%}")
                print(f"Average LOS Improvement: {avg_improvement:.2f} hours")
        
        eval_btn.on_click(run_evaluation)
        
        display(W.VBox([
            W.HTML("<b>ED State Awareness System</b>"),
            state_toggle,
            W.HBox([state_btn, eval_btn]),
            state_out,
            eval_out
        ]))
        
    except Exception as e:
        print("State awareness UI unavailable:", e)

print("ED State Classification System loaded")
print("- Use state_aware_gate_engine() for state-based coordination")
print("- Set CONFIG['USE_STATE_AWARENESS'] = True to enable")
print("- Call add_state_awareness_ui() for research controls")