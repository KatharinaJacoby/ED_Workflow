# === GATE ENGINE - PRIMARY DECISION SYSTEM ===
# Drop this cell after your ML bridge cell (around cell 11-12)
# Gate engine = primary decision maker, MLP = secondary refinement when stable

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import json
import numpy as np

@dataclass
class GateStatus:
    """Individual gate assessment result"""
    category: str
    gate_id: str
    status: str  # "open", "blocked", "pending"
    readiness_score: float  # 0.0-1.0
    blockers: List[str]
    eta_minutes: Optional[int]
    actions_required: List[str]
    confidence: float = 1.0  # Gate engine is deterministic, always confident

class OperationalGateEngine:
    """
    PRIMARY DECISION SYSTEM for ED workflow management
    - Deterministic, interpretable, operationally-focused
    - Uses your existing 16-feature structure
    - Integrates with WorkflowState and clinical calculators
    - MLP provides secondary input when available (calibrated)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # PROTECTED operational constraints (your domain expertise - cannot be overridden)
        self.CONSTRAINTS = {
            "bed_manager_cutoff_hour": 16,  # 4pm - transfers become difficult
            "night_shift_start_hour": 22,   # 10pm - ward deflection increases  
            "troponin_delta_hours": 3,      # Standard protocol
            "mandatory_hold_conditions": ["abdominal", "abdom"],  # Brittle codes
            "ct_queue_threshold_minutes": 120,
            "lab_turnaround_threshold_minutes": 90,
            "icu_critical_threshold": 2,    # ICU beds remaining = critical
            "boarding_threshold_minutes": 300,  # 5 hours = boarding
            "high_acuity_time_limit": 120,  # 2 hours max for Tag=1 patients
        }
        
        # Feature mapping for your 16-feature structure
        self.REQUIRED_FEATURES = [
            'Tag', 't_min', 'Triage', 'Leitsymptom', 'HF', 'MAP', 
            'ICU_Kap', 'Kap_veraltet', 't_norm', 'hat_Labor', 'Labor_ausstehend',
            'hat_Roentgen', 'Roentgen_ausstehend', 'hat_CT', 'CT_ausstehend', 'naechste_Aktion'
        ]
        
        print(f"🚪 Gate Engine initialized with {len(self.CONSTRAINTS)} protected constraints")
    
    def assess_medical_completion(self, features: Dict[str, Any], calculators: Dict[str, Any] = None) -> GateStatus:
        """
        Gate 1: Medical workup completion assessment
        CANNOT be overridden by MLP - medical safety protocols are non-negotiable
        """
        blockers = []
        actions = []
        score = 1.0
        eta = None
        
        # Lab completion check
        if not features.get('hat_Labor', False):
            blockers.append("No initial labs ordered")
            actions.append("Order baseline labs (CBC, BMP, PT/INR)")
            score *= 0.2
        elif features.get('Labor_ausstehend', False):
            blockers.append("Lab results pending")
            actions.append("Follow up pending lab results")
            score *= 0.6
            eta = self.CONSTRAINTS["lab_turnaround_threshold_minutes"]
        
        # Imaging completion
        if features.get('CT_ausstehend', False):
            blockers.append("CT scan pending")
            actions.append("Follow up CT results - contact radiology if delayed")
            score *= 0.4
            eta = max(eta or 0, self.CONSTRAINTS["ct_queue_threshold_minutes"])
        
        if features.get('Roentgen_ausstehend', False):
            blockers.append("X-ray pending")
            actions.append("Follow up X-ray results")
            score *= 0.7
        
        # Clinical calculator integration
        if calculators:
            # HEART score protocol (chest pain)
            heart_score = calculators.get('heart', 0)
            if heart_score >= 4:
                blockers.append("High HEART score - incomplete cardiac workup")
                actions.append("Complete serial troponins, consider cardiology consult")
                score *= 0.3
                eta = max(eta or 0, 180)  # 3hr troponin protocol
            
            # qSOFA protocol (sepsis concern)
            qsofa_score = calculators.get('qsofa', 0)
            if qsofa_score >= 2:
                blockers.append("Sepsis concern - incomplete bundle")
                actions.append("Complete sepsis bundle: cultures, lactate, antibiotics")
                score *= 0.2
                eta = max(eta or 0, 60)  # 1hr sepsis bundle
            
            # Troponin delta protocol
            if calculators.get('troponin_flag', False):
                blockers.append("Troponin delta protocol incomplete")
                actions.append("Complete 3-hour troponin series")
                score *= 0.4
                eta = max(eta or 0, self.CONSTRAINTS["troponin_delta_hours"] * 60)
        
        # Next action documentation
        naechste_aktion = features.get('naechste_Aktion', '').lower()
        if naechste_aktion in ['unknown', '', 'none']:
            blockers.append("Disposition plan unclear")
            actions.append("Document clear disposition plan and next steps")
            score *= 0.7
        
        status = "open" if score > 0.8 else ("pending" if score > 0.3 else "blocked")
        
        return GateStatus(
            category="medical_completion",
            gate_id="workup_complete",
            status=status,
            readiness_score=score,
            blockers=blockers,
            eta_minutes=eta,
            actions_required=actions,
            confidence=1.0
        )
    
    def assess_operational_timing(self, features: Dict[str, Any], current_time: datetime = None) -> GateStatus:
        """
        Gate 2: Operational timing constraints
        Based on your real operational knowledge - bed managers, night shift patterns
        """
        if not current_time:
            current_time = datetime.now()
        
        blockers = []
        actions = []
        score = 1.0
        eta = None
        hour = current_time.hour
        
        # Bed manager availability (PROTECTED CONSTRAINT)
        if hour >= self.CONSTRAINTS["bed_manager_cutoff_hour"]:
            blockers.append("Bed managers off duty after 4pm")
            actions.append("Use emergency bed request or wait until morning")
            score *= 0.3
            # ETA until next business day 8am
            hours_until_8am = (32 - hour) % 24  # Next day 8am
            eta = hours_until_8am * 60
        
        # Night shift resistance pattern (PROTECTED CONSTRAINT)
        if hour >= self.CONSTRAINTS["night_shift_start_hour"] or hour < 6:
            blockers.append("Night shift transfer resistance")
            actions.append("Strong clinical justification required for night transfer")
            score *= 0.6
        
        # Weekend effects
        if current_time.weekday() >= 5:  # Saturday/Sunday
            blockers.append("Weekend - reduced capacity")
            actions.append("Limited transfer options on weekends")
            score *= 0.8
        
        # ICU capacity constraints
        icu_kap = features.get('ICU_Kap', 10)
        if icu_kap <= self.CONSTRAINTS["icu_critical_threshold"]:
            blockers.append(f"ICU critically low ({icu_kap} beds remaining)")
            actions.append("Contact ICU attending for bed availability")
            score *= 0.2
            eta = max(eta or 0, 240)  # 4hr typical ICU turnover
        
        # Outdated capacity data
        if features.get('Kap_veraltet', False):
            blockers.append("ICU capacity data is stale")
            actions.append("Update real-time ICU bed availability")
            score *= 0.9
        
        status = "open" if score > 0.7 else ("pending" if score > 0.4 else "blocked")
        
        return GateStatus(
            category="operational_timing",
            gate_id="bed_flow",
            status=status,
            readiness_score=score,
            blockers=blockers,
            eta_minutes=eta,
            actions_required=actions,
            confidence=1.0
        )
    
    def assess_clinical_safety(self, features: Dict[str, Any], calculators: Dict[str, Any] = None) -> GateStatus:
        """
        Gate 3: Clinical safety protocols (PROTECTED - cannot be overridden)
        Your operational knowledge of mandatory holds and safety rails
        """
        blockers = []
        actions = []
        score = 1.0
        eta = None
        
        leitsymptom = str(features.get('Leitsymptom', '')).lower()
        
        # Mandatory hold conditions (PROTECTED CONSTRAINT)
        for condition in self.CONSTRAINTS["mandatory_hold_conditions"]:
            if condition in leitsymptom:
                blockers.append(f"Mandatory 24hr hold - {condition} pain protocol")
                actions.append("Serial exams, repeat labs, surgical consultation")
                score *= 0.1  # Almost always blocked
                eta = 24 * 60  # 24 hour hold
                break
        
        # High acuity time limits (PROTECTED CONSTRAINT)
        t_min = features.get('t_min', 0)
        tag = features.get('Tag', 5)
        if tag == 1 and t_min > self.CONSTRAINTS["high_acuity_time_limit"]:
            blockers.append("High acuity patient >2hr without disposition")
            actions.append("Urgent senior review - check for missed interventions")
            score *= 0.4
        
        # Boarding threshold (PROTECTED CONSTRAINT)
        if t_min > self.CONSTRAINTS["boarding_threshold_minutes"]:
            blockers.append(f"Patient boarding >5 hours")
            actions.append("Expedite disposition - contact bed management")
            score *= 0.5
        
        # Clinical calculator safety checks
        if calculators:
            # High-risk chest pain (cannot discharge without complete workup)
            if 'chest' in leitsymptom and calculators.get('heart', 0) >= 6:
                blockers.append("High-risk chest pain - incomplete evaluation")
                actions.append("Mandatory cardiology evaluation before discharge")
                score *= 0.2
            
            # Septic shock screening
            if calculators.get('qsofa', 0) >= 3:
                blockers.append("Potential septic shock")
                actions.append("ICU evaluation required - cannot discharge")
                score *= 0.1
        
        # Minimum observation time
        if t_min < 30:  # Less than 30 minutes
            blockers.append("Insufficient observation time")
            actions.append("Continue monitoring - minimum ED stay not met")
            score *= 0.8
            eta = max(eta or 0, 30 - t_min)
        
        status = "open" if score > 0.8 else ("pending" if score > 0.4 else "blocked")
        
        return GateStatus(
            category="clinical_safety",
            gate_id="safety_protocols", 
            status=status,
            readiness_score=score,
            blockers=blockers,
            eta_minutes=eta,
            actions_required=actions,
            confidence=1.0
        )
    
    def assess_resource_availability(self, features: Dict[str, Any]) -> GateStatus:
        """
        Gate 4: Resource constraint assessment
        CT queues, lab turnaround, capacity bottlenecks
        """
        blockers = []
        actions = []
        score = 1.0
        eta = None
        
        t_min = features.get('t_min', 0)
        
        # CT queue bottleneck
        if features.get('CT_ausstehend', False):
            # If CT has been pending for a long time, it's a resource constraint
            if t_min > 180:  # 3+ hours with pending CT
                blockers.append("CT queue severely delayed")
                actions.append("Escalate to radiology - consider clinical decision without CT")
                score *= 0.4
                eta = 60  # Escalation should resolve in 1hr
            else:
                score *= 0.7  # Normal CT wait
        
        # Lab turnaround pressure
        if features.get('Labor_ausstehend', False) and t_min > self.CONSTRAINTS["lab_turnaround_threshold_minutes"]:
            blockers.append("Lab results significantly overdue")
            actions.append("Contact lab for urgent results")
            score *= 0.6
        
        # ICU capacity pressure
        icu_kap = features.get('ICU_Kap', 10)
        if icu_kap <= 1:  # Critical ICU capacity
            blockers.append("ICU at capacity")
            actions.append("Consider step-down unit or delay elective admissions")
            score *= 0.3
        elif icu_kap <= 3:  # Low capacity
            blockers.append("ICU capacity limited")
            actions.append("Prioritize ICU-appropriate patients only")
            score *= 0.6
        
        # Overall system pressure (multiple pending items)
        pending_count = sum([
            features.get('Labor_ausstehend', False),
            features.get('CT_ausstehend', False), 
            features.get('Roentgen_ausstehend', False)
        ])
        
        if pending_count >= 2:
            blockers.append("Multiple pending results - system overload")
            actions.append("Prioritize most critical results first")
            score *= 0.7
        
        status = "open" if score > 0.7 else ("pending" if score > 0.4 else "blocked")
        
        return GateStatus(
            category="resource_availability",
            gate_id="system_capacity",
            status=status,
            readiness_score=score,
            blockers=blockers,
            eta_minutes=eta,
            actions_required=actions,
            confidence=1.0
        )
    
    def compute_overall_readiness(self, features: Dict[str, Any], calculators: Dict[str, Any] = None, 
                                patient_context: Dict[str, Any] = None, current_time: datetime = None) -> Dict[str, Any]:
        """
        PRIMARY DECISION COMPUTATION
        Gate engine determines operational readiness - MLP provides supplementary input only
        """
        
        # Ensure all required features are present with defaults
        complete_features = {}
        feature_defaults = {
            'Tag': 3, 't_min': 120, 'Triage': 3, 'Leitsymptom': 'unknown',
            'HF': 80, 'MAP': 80, 'ICU_Kap': 5, 'Kap_veraltet': False,
            't_norm': 1.0, 'hat_Labor': True, 'Labor_ausstehend': False,
            'hat_Roentgen': True, 'Roentgen_ausstehend': False,
            'hat_CT': False, 'CT_ausstehend': False, 'naechste_Aktion': 'unknown'
        }
        
        for key, default in feature_defaults.items():
            complete_features[key] = features.get(key, default)
        
        # Run all gate assessments
        current_time = current_time or datetime.now()
        
        gates = {
            'medical_completion': self.assess_medical_completion(complete_features, calculators),
            'operational_timing': self.assess_operational_timing(complete_features, current_time),
            'clinical_safety': self.assess_clinical_safety(complete_features, calculators),
            'resource_availability': self.assess_resource_availability(complete_features)
        }
        
        # WEIGHTED SCORING (operational priorities)
        weights = {
            'clinical_safety': 0.4,      # Safety first - cannot be compromised
            'medical_completion': 0.3,    # Medical readiness critical
            'operational_timing': 0.2,    # Timing affects but doesn't override safety
            'resource_availability': 0.1  # Resources are constraints, not blockers
        }
        
        # Overall readiness calculation
        overall_score = sum(gates[category].readiness_score * weight 
                          for category, weight in weights.items())
        
        # Priority calculation (higher score = higher priority for staff attention)
        # Inverse relationship: lower readiness = higher priority
        base_priority = max(1, int(10 * (1 - overall_score)))
        
        # Priority adjustments based on clinical factors
        priority_adjustments = 0
        
        # High acuity always gets priority boost
        if complete_features.get('Tag') == 1:
            priority_adjustments += 2
        if complete_features.get('Triage', 5) <= 2:
            priority_adjustments += 1
        
        # Time-based priority (boarding patients need attention)
        t_min = complete_features.get('t_min', 0)
        if t_min > 480:  # >8 hours
            priority_adjustments += 2
        elif t_min > 240:  # >4 hours  
            priority_adjustments += 1
        
        final_priority = min(10, base_priority + priority_adjustments)
        
        # Next action prioritization (most critical gate drives action)
        all_actions = []
        critical_gates = []
        
        for category, gate in gates.items():
            if gate.status == "blocked":
                critical_gates.append(f"{category} BLOCKED")
                all_actions.extend(gate.actions_required[:2])  # Top 2 actions per gate
            elif gate.status == "pending":
                all_actions.extend(gate.actions_required[:1])  # Top 1 action for pending
        
        next_action = all_actions[0] if all_actions else "Ready for disposition"
        
        # Status badge generation
        status_counts = {"open": 0, "pending": 0, "blocked": 0}
        for gate in gates.values():
            status_counts[gate.status] += 1
        
        gate_summary = f"🟢{status_counts['open']} 🟡{status_counts['pending']} 🔴{status_counts['blocked']}"
        
        # ETA calculation (longest blocking constraint)
        max_eta = None
        for gate in gates.values():
            if gate.eta_minutes and (max_eta is None or gate.eta_minutes > max_eta):
                max_eta = gate.eta_minutes
        
        # MLP integration (SECONDARY INPUT ONLY - cannot override gate decisions)
        mlp_input = None
        mlp_useful = False
        
        try:
            if 'predict_one' in globals():
                # Use your existing ML bridge
                mlp_result = predict_one(complete_features)
                mlp_input = mlp_result
                
                # MLP is only "useful" if it provides meaningful signal
                # Your current model has threshold 99.88% - essentially useless
                mlp_useful = mlp_result.get('p', 0) > 0.01  # More than 1% probability
                
                # If MLP is actually useful (after you fix it), use it to REFINE priority
                if mlp_useful and mlp_result.get('p', 0) > 0.5:
                    # MLP suggests higher risk - can increase priority but not decrease
                    # This ensures gate engine decisions are protected
                    if final_priority < 8:  # Don't max out already high priority
                        final_priority = min(10, final_priority + 1)
        except Exception as e:
            mlp_input = {"error": str(e)}
        
        return {
            'overall_readiness': overall_score,
            'priority': final_priority,
            'gates': gate_summary,
            'next_action': next_action,
            'eta_minutes': max_eta,
            'gate_details': gates,
            'mlp_input': mlp_input,
            'mlp_useful': mlp_useful,
            'critical_gates': critical_gates,
            'computed_at': current_time.isoformat(),
            'decision_basis': 'gate_engine_primary'  # Clear decision source
        }

# Initialize global gate engine
gate_engine = OperationalGateEngine()

# Enhanced scoring function that replaces your score_and_log
def score_and_gate(row: dict, calculators: dict = None, patient_context: dict = None) -> dict:
    """
    ENHANCED SCORING FUNCTION - Gate-first approach
    - Gate engine = primary decision maker
    - MLP = secondary input (when calibrated and stable)  
    - Integrates with your existing clinical calculators
    """
    
    # Primary decision: Gate engine assessment
    gate_result = gate_engine.compute_overall_readiness(row, calculators, patient_context)
    
    # Display results
    print(f"🚪 Gate Engine Assessment:")
    print(f"   Priority: {gate_result['priority']}/10 | Readiness: {gate_result['overall_readiness']:.2f}")
    print(f"   Status: {gate_result['gates']}")
    print(f"   Next Action: {gate_result['next_action']}")
    
    if gate_result.get('critical_gates'):
        print(f"   🔴 Critical: {', '.join(gate_result['critical_gates'])}")
    
    if gate_result.get('eta_minutes'):
        hours = gate_result['eta_minutes'] // 60
        mins = gate_result['eta_minutes'] % 60
        eta_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
        print(f"   ⏱️ ETA: {eta_str}")
    
    # Secondary input: MLP (for comparison/future calibration)
    mlp_result = gate_result.get('mlp_input', {})
    if mlp_result and not mlp_result.get('error'):
        useful = "✅" if gate_result.get('mlp_useful', False) else "❌"
        print(f"   {useful} MLP: p={mlp_result.get('p', 0):.6f} → {'ALERT' if mlp_result.get('y', 0) else 'ok'}")
        if not gate_result.get('mlp_useful', False):
            print(f"      ↳ MLP not useful (threshold={mlp_result.get('thr', 'unknown'):.4f})")
    
    # Event logging
    _append_event({
        "type": "gate_primary_assessment",
        "patient_id": row.get("Fall-ID", "unknown"),
        "gate_priority": gate_result['priority'],
        "gate_readiness": gate_result['overall_readiness'], 
        "gate_status": gate_result['gates'],
        "next_action": gate_result['next_action'],
        "eta_minutes": gate_result.get('eta_minutes'),
        "critical_gates": gate_result.get('critical_gates', []),
        "mlp_useful": gate_result.get('mlp_useful', False),
        "mlp_result": mlp_result,
        "decision_basis": "gate_engine_primary",
        "calculators": calculators or {}
    })
    
    return {
        "gate_result": gate_result,
        "primary_decision": gate_result,  # Gate engine drives decisions
        "operational_priority": gate_result['priority'],
        "next_actions": gate_result.get('gate_details', {})
    }

# WorkflowState integration
def process_workflow_state_gate(state: WorkflowState, calculators: dict = None) -> dict:
    """
    Enhanced WorkflowState processing with gate-first approach
    Integrates with your existing WorkflowState.feature_dict() method
    """
    features = state.feature_dict()
    
    # Extract patient context from WorkflowState
    patient_context = {
        'age': features.get('age', state.state.get('age', 65)),
        'role': state.role,
        'alerts_count': len(state.alerts),
        'since_vitals_min': state.state.get('since_vitals_min', 0.0)
    }
    
    return score_and_gate(features, calculators, patient_context)

# Backward compatibility - replace your existing score_and_log
score_and_log = score_and_gate

print("✅ Gate Engine Ready - Primary Decision System")
print(f"   🔒 {len(gate_engine.CONSTRAINTS)} protected operational constraints")
print(f"   🧮 Integrates with your clinical calculators")  
print(f"   📊 Uses your existing 16-feature structure")
print(f"   🔄 Compatible with WorkflowState and event logging")
print(f"   🤖 MLP provides secondary input when available")
print("\n💡 Gate engine = PRIMARY, MLP = SECONDARY refinement")
print("   Use: score_and_gate(patient_features, calculators, patient_context)")