# === Enhanced ED Coordinator: Complete Operational Workflow Management ===
# Focus: Real-time coordination, clinical decision support, system integration
# Based on clinical feedback - NOT patient prioritization

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Set, Callable, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
from abc import ABC, abstractmethod
import asyncio
from collections import defaultdict, deque
import re

# Configure logging for operational tracking
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiagnosticStatus(Enum):
    ORDERED = "ordered"
    PENDING = "pending" 
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEWED = "reviewed"
    CANCELLED = "cancelled"

class HandoffStage(Enum):
    EMS_ARRIVAL = "ems_arrival"
    TRIAGE_COMPLETE = "triage_complete"
    WORKUP_ACTIVE = "workup_active"
    AWAITING_RESULTS = "awaiting_results"
    DIAGNOSIS_CLEAR = "diagnosis_clear"
    TREATMENT_ACTIVE = "treatment_active"
    TREATMENT_PLAN = "treatment_plan"
    READY_TRANSFER = "ready_transfer"
    TRANSFERRED = "transferred"
    DISCHARGED = "discharged"

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    URGENT = "urgent"
    CRITICAL = "critical"

class ClinicalProtocol(Enum):
    CHEST_PAIN = "chest_pain"
    ABDOMINAL_PAIN = "abdominal_pain"
    DYSPNEA = "dyspnea"
    NEUROLOGICAL = "neurological"
    TRAUMA = "trauma"
    SEPSIS = "sepsis"
    GENERAL = "general"

@dataclass
class DiagnosticOrder:
    test_type: str
    ordered_at: datetime
    ordered_by: str
    status: DiagnosticStatus = DiagnosticStatus.ORDERED
    expected_completion: Optional[datetime] = None
    result_available_at: Optional[datetime] = None
    critical_result: bool = False
    result_summary: Optional[str] = None
    result_data: Dict[str, Any] = field(default_factory=dict)
    priority: str = "routine"  # routine, urgent, stat
    department: Optional[str] = None  # radiology, lab, cardiology
    
    def is_overdue(self, threshold_minutes: int = 30) -> bool:
        """Check if diagnostic is overdue"""
        if not self.expected_completion:
            return False
        return (datetime.now() > self.expected_completion + timedelta(minutes=threshold_minutes) 
                and self.status not in [DiagnosticStatus.COMPLETED, DiagnosticStatus.REVIEWED])
    
    def time_to_completion(self) -> Optional[timedelta]:
        """Calculate expected time to completion"""
        if self.status in [DiagnosticStatus.COMPLETED, DiagnosticStatus.REVIEWED]:
            return timedelta(0)
        if self.expected_completion:
            remaining = self.expected_completion - datetime.now()
            return remaining if remaining > timedelta(0) else timedelta(0)
        return None

@dataclass
class ClinicalAlert:
    alert_id: str
    patient_id: str
    severity: AlertSeverity
    message: str
    created_at: datetime
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    resolved: bool = False
    category: str = "general"
    
    def acknowledge(self, staff_id: str):
        """Acknowledge alert"""
        self.acknowledged = True
        self.acknowledged_by = staff_id
    
    def resolve(self):
        """Mark alert as resolved"""
        self.resolved = True

@dataclass
class HandoffPackage:
    """Complete information package for ward/GP handoff"""
    diagnosis: Optional[str] = None
    differential_diagnoses: List[str] = field(default_factory=list)
    treatment_plan: Optional[str] = None
    completed_treatments: List[str] = field(default_factory=list)
    pending_actions: List[str] = field(default_factory=list)
    medications: List[Dict[str, str]] = field(default_factory=list)  # name, dose, frequency
    allergies: List[str] = field(default_factory=list)
    follow_up_needed: List[str] = field(default_factory=list)
    social_factors: List[str] = field(default_factory=list)
    specialist_notes: Optional[str] = None
    discharge_instructions: Optional[str] = None
    complete: bool = False
    prepared_by: Optional[str] = None
    prepared_at: Optional[datetime] = None
    
    def validate_completeness(self) -> List[str]:
        """Return list of missing required fields"""
        missing = []
        if not self.diagnosis:
            missing.append("Primary diagnosis")
        if not self.treatment_plan:
            missing.append("Treatment plan")
        if not self.medications and not self.discharge_instructions:
            missing.append("Medications or discharge instructions")
        return missing
    
    def mark_complete(self, staff_id: str):
        """Mark handoff package as complete"""
        missing = self.validate_completeness()
        if not missing:
            self.complete = True
            self.prepared_by = staff_id
            self.prepared_at = datetime.now()
            return True
        return False

@dataclass 
class VitalSigns:
    timestamp: datetime
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    heart_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    temperature: Optional[float] = None
    oxygen_saturation: Optional[int] = None
    pain_score: Optional[int] = None
    
    def is_abnormal(self) -> List[str]:
        """Return list of abnormal vital signs"""
        abnormal = []
        if self.systolic_bp and (self.systolic_bp > 180 or self.systolic_bp < 90):
            abnormal.append(f"Systolic BP: {self.systolic_bp}")
        if self.heart_rate and (self.heart_rate > 120 or self.heart_rate < 50):
            abnormal.append(f"Heart rate: {self.heart_rate}")
        if self.respiratory_rate and (self.respiratory_rate > 24 or self.respiratory_rate < 8):
            abnormal.append(f"Respiratory rate: {self.respiratory_rate}")
        if self.temperature and (self.temperature > 38.5 or self.temperature < 35.0):
            abnormal.append(f"Temperature: {self.temperature}°C")
        if self.oxygen_saturation and self.oxygen_saturation < 92:
            abnormal.append(f"Oxygen saturation: {self.oxygen_saturation}%")
        return abnormal

@dataclass
class PatientWorkflow:
    patient_id: str
    arrival_time: datetime
    current_stage: HandoffStage = HandoffStage.EMS_ARRIVAL
    
    # Patient information
    chief_complaint: Optional[str] = None
    ems_notes: Optional[str] = None
    triage_notes: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    comorbidities: List[str] = field(default_factory=list)
    
    # Clinical tracking
    vital_signs_history: List[VitalSigns] = field(default_factory=list)
    diagnostics: Dict[str, DiagnosticOrder] = field(default_factory=dict)
    clinical_protocol: Optional[ClinicalProtocol] = None
    
    # Handoff preparation
    handoff_package: HandoffPackage = field(default_factory=HandoffPackage)
    target_department: Optional[str] = None
    estimated_los: Optional[timedelta] = None
    
    # Operational tracking
    bed_assigned: Optional[str] = None
    staff_assigned: Set[str] = field(default_factory=set)
    alerts: List[ClinicalAlert] = field(default_factory=list)
    last_update: datetime = field(default_factory=datetime.now)
    
    # Communication log
    communication_events: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_vital_signs(self, vitals: VitalSigns):
        """Add new vital signs measurement"""
        self.vital_signs_history.append(vitals)
        self.last_update = datetime.now()
        
        # Check for abnormal values and create alerts
        abnormal = vitals.is_abnormal()
        if abnormal:
            alert = ClinicalAlert(
                alert_id=f"VS_{self.patient_id}_{int(datetime.now().timestamp())}",
                patient_id=self.patient_id,
                severity=AlertSeverity.WARNING,
                message=f"Abnormal vital signs: {', '.join(abnormal)}",
                created_at=datetime.now(),
                category="vital_signs"
            )
            self.alerts.append(alert)
    
    def get_latest_vitals(self) -> Optional[VitalSigns]:
        """Get most recent vital signs"""
        return self.vital_signs_history[-1] if self.vital_signs_history else None
    
    def add_diagnostic_order(self, test_type: str, ordered_by: str, 
                           expected_minutes: int = 60, priority: str = "routine",
                           department: str = "lab"):
        """Add diagnostic order with clinical context"""
        order = DiagnosticOrder(
            test_type=test_type,
            ordered_at=datetime.now(),
            ordered_by=ordered_by,
            expected_completion=datetime.now() + timedelta(minutes=expected_minutes),
            priority=priority,
            department=department
        )
        self.diagnostics[test_type] = order
        self.last_update = datetime.now()
        
        # Log communication event
        self.communication_events.append({
            "timestamp": datetime.now().isoformat(),
            "event": "diagnostic_ordered",
            "test": test_type,
            "priority": priority,
            "ordered_by": ordered_by
        })
    
    def update_diagnostic_status(self, test_type: str, status: DiagnosticStatus, 
                               result_summary: Optional[str] = None, 
                               critical: bool = False,
                               result_data: Dict[str, Any] = None):
        """Update diagnostic status with enhanced tracking"""
        if test_type not in self.diagnostics:
            logger.warning(f"Diagnostic {test_type} not found for patient {self.patient_id}")
            return False
        
        order = self.diagnostics[test_type]
        old_status = order.status
        order.status = status
        
        if status == DiagnosticStatus.COMPLETED:
            order.result_available_at = datetime.now()
            order.critical_result = critical
            order.result_summary = result_summary
            if result_data:
                order.result_data = result_data
            
            # Create alert for critical results
            if critical:
                alert = ClinicalAlert(
                    alert_id=f"CRIT_{self.patient_id}_{test_type}_{int(datetime.now().timestamp())}",
                    patient_id=self.patient_id,
                    severity=AlertSeverity.CRITICAL,
                    message=f"CRITICAL RESULT: {test_type} - {result_summary}",
                    created_at=datetime.now(),
                    category="critical_result"
                )
                self.alerts.append(alert)
        
        self.last_update = datetime.now()
        
        # Log status change
        self.communication_events.append({
            "timestamp": datetime.now().isoformat(),
            "event": "diagnostic_updated",
            "test": test_type,
            "old_status": old_status.value,
            "new_status": status.value,
            "critical": critical
        })
        
        return True
    
    def advance_stage(self, new_stage: HandoffStage, staff_id: Optional[str] = None):
        """Advance workflow stage with validation"""
        old_stage = self.current_stage
        
        # Validate stage transition (basic validation)
        valid_transitions = {
            HandoffStage.EMS_ARRIVAL: [HandoffStage.TRIAGE_COMPLETE],
            HandoffStage.TRIAGE_COMPLETE: [HandoffStage.WORKUP_ACTIVE],
            HandoffStage.WORKUP_ACTIVE: [HandoffStage.AWAITING_RESULTS, HandoffStage.DIAGNOSIS_CLEAR],
            HandoffStage.AWAITING_RESULTS: [HandoffStage.DIAGNOSIS_CLEAR, HandoffStage.WORKUP_ACTIVE],
            HandoffStage.DIAGNOSIS_CLEAR: [HandoffStage.TREATMENT_ACTIVE, HandoffStage.TREATMENT_PLAN],
            HandoffStage.TREATMENT_ACTIVE: [HandoffStage.TREATMENT_PLAN],
            HandoffStage.TREATMENT_PLAN: [HandoffStage.READY_TRANSFER],
            HandoffStage.READY_TRANSFER: [HandoffStage.TRANSFERRED, HandoffStage.DISCHARGED]
        }
        
        if new_stage in valid_transitions.get(self.current_stage, []):
            self.current_stage = new_stage
            self.last_update = datetime.now()
            
            # Log stage advancement
            self.communication_events.append({
                "timestamp": datetime.now().isoformat(),
                "event": "stage_advanced",
                "old_stage": old_stage.value,
                "new_stage": new_stage.value,
                "staff_id": staff_id
            })
            
            return True
        else:
            logger.warning(f"Invalid stage transition from {old_stage} to {new_stage}")
            return False
    
    def get_pending_diagnostics(self) -> List[str]:
        """Return diagnostics still pending completion"""
        return [test for test, order in self.diagnostics.items() 
                if order.status in [DiagnosticStatus.ORDERED, DiagnosticStatus.PENDING, DiagnosticStatus.IN_PROGRESS]]
    
    def get_overdue_diagnostics(self, threshold_minutes: int = 30) -> List[str]:
        """Return overdue diagnostics"""
        return [test for test, order in self.diagnostics.items() 
                if order.is_overdue(threshold_minutes)]
    
    def get_critical_alerts(self) -> List[ClinicalAlert]:
        """Get unresolved critical alerts"""
        return [alert for alert in self.alerts 
                if alert.severity == AlertSeverity.CRITICAL and not alert.resolved]
    
    def is_handoff_ready(self) -> bool:
        """Comprehensive check for handoff readiness"""
        return (
            self.current_stage == HandoffStage.READY_TRANSFER and
            self.handoff_package.complete and
            len(self.get_pending_diagnostics()) == 0 and
            len(self.get_critical_alerts()) == 0
        )
    
    def estimate_completion_time(self) -> Optional[datetime]:
        """Estimate when patient will be ready for handoff"""
        pending = self.get_pending_diagnostics()
        if not pending:
            return datetime.now()  # Ready now
        
        # Find latest expected completion time
        latest_completion = None
        for test in pending:
            if test in self.diagnostics:
                completion_time = self.diagnostics[test].time_to_completion()
                if completion_time:
                    estimated = datetime.now() + completion_time
                    if not latest_completion or estimated > latest_completion:
                        latest_completion = estimated
        
        return latest_completion

class ClinicalProtocolEngine:
    """Evidence-based clinical decision support"""
    
    def __init__(self):
        self.protocols = self._initialize_protocols()
    
    def _initialize_protocols(self) -> Dict[ClinicalProtocol, Dict]:
        """Initialize clinical protocols based on guidelines"""
        return {
            ClinicalProtocol.CHEST_PAIN: {
                "diagnostic_orders": {
                    "ECG": {"priority": "stat", "expected_minutes": 10, "department": "cardiology"},
                    "troponin_serial": {"priority": "urgent", "expected_minutes": 30, "department": "lab"},
                    "chest_xray": {"priority": "urgent", "expected_minutes": 45, "department": "radiology"},
                    "d_dimer": {"priority": "routine", "expected_minutes": 60, "department": "lab"}
                },
                "critical_timeframes": {"ECG": 10, "troponin": 30},
                "escalation_criteria": ["troponin_positive", "ECG_changes", "ongoing_pain"],
                "discharge_criteria": ["negative_workup", "pain_free", "low_risk_score"]
            },
            ClinicalProtocol.ABDOMINAL_PAIN: {
                "diagnostic_orders": {
                    "blood_panel": {"priority": "urgent", "expected_minutes": 45, "department": "lab"},
                    "urinalysis": {"priority": "routine", "expected_minutes": 30, "department": "lab"},
                    "abdominal_ultrasound": {"priority": "urgent", "expected_minutes": 60, "department": "radiology"},
                    "CT_abdomen": {"priority": "urgent", "expected_minutes": 90, "department": "radiology"}
                },
                "critical_timeframes": {"blood_panel": 60},
                "escalation_criteria": ["peritoneal_signs", "unstable_vitals", "severe_pain"],
                "discharge_criteria": ["negative_imaging", "normal_labs", "pain_resolved"]
            },
            ClinicalProtocol.DYSPNEA: {
                "diagnostic_orders": {
                    "ECG": {"priority": "urgent", "expected_minutes": 15, "department": "cardiology"},
                    "chest_xray": {"priority": "urgent", "expected_minutes": 30, "department": "radiology"},
                    "ABG": {"priority": "urgent", "expected_minutes": 20, "department": "lab"},
                    "BNP": {"priority": "routine", "expected_minutes": 60, "department": "lab"},
                    "d_dimer": {"priority": "routine", "expected_minutes": 60, "department": "lab"}
                },
                "critical_timeframes": {"ABG": 30, "chest_xray": 45},
                "escalation_criteria": ["hypoxemia", "respiratory_failure", "hemodynamic_instability"],
                "discharge_criteria": ["stable_oxygen", "normal_imaging", "symptom_resolution"]
            }
        }
    
    def suggest_diagnostic_pathway(self, patient: PatientWorkflow) -> List[Dict[str, Any]]:
        """Generate evidence-based diagnostic recommendations"""
        if not patient.clinical_protocol:
            protocol = self._determine_protocol(patient.chief_complaint or "")
            patient.clinical_protocol = protocol
        else:
            protocol = patient.clinical_protocol
        
        if protocol not in self.protocols:
            protocol = ClinicalProtocol.GENERAL
        
        protocol_data = self.protocols.get(protocol, {})
        diagnostic_orders = protocol_data.get("diagnostic_orders", {})
        
        suggestions = []
        for test, config in diagnostic_orders.items():
            if test not in patient.diagnostics:  # Only suggest if not already ordered
                suggestions.append({
                    "test": test,
                    "priority": config["priority"],
                    "expected_minutes": config["expected_minutes"],
                    "department": config["department"],
                    "rationale": f"Standard {protocol.value} workup"
                })
        
        return suggestions
    
    def _determine_protocol(self, chief_complaint: str) -> ClinicalProtocol:
        """Determine appropriate clinical protocol"""
        complaint = chief_complaint.lower()
        
        if any(term in complaint for term in ["chest pain", "cardiac", "heart"]):
            return ClinicalProtocol.CHEST_PAIN
        elif any(term in complaint for term in ["abdominal pain", "stomach", "nausea", "vomiting"]):
            return ClinicalProtocol.ABDOMINAL_PAIN
        elif any(term in complaint for term in ["shortness of breath", "dyspnea", "breathing"]):
            return ClinicalProtocol.DYSPNEA
        elif any(term in complaint for term in ["neurological", "confusion", "headache", "weakness"]):
            return ClinicalProtocol.NEUROLOGICAL
        elif any(term in complaint for term in ["trauma", "injury", "accident"]):
            return ClinicalProtocol.TRAUMA
        elif any(term in complaint for term in ["fever", "infection", "sepsis"]):
            return ClinicalProtocol.SEPSIS
        else:
            return ClinicalProtocol.GENERAL
    
    def check_protocol_compliance(self, patient: PatientWorkflow) -> Dict[str, Any]:
        """Check compliance with clinical protocols"""
        if not patient.clinical_protocol:
            return {"compliant": True, "violations": []}
        
        protocol_data = self.protocols.get(patient.clinical_protocol, {})
        timeframes = protocol_data.get("critical_timeframes", {})
        
        violations = []
        for test, max_minutes in timeframes.items():
            if test in patient.diagnostics:
                order = patient.diagnostics[test]
                time_since_order = datetime.now() - order.ordered_at
                if (time_since_order.total_seconds() / 60 > max_minutes and 
                    order.status != DiagnosticStatus.COMPLETED):
                    violations.append(f"{test} overdue (>{max_minutes} minutes)")
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "protocol": patient.clinical_protocol.value if patient.clinical_protocol else None
        }

class EnhancedCapacityMonitor:
    """Advanced capacity monitoring with bottleneck prediction"""
    
    def __init__(self):
        self.bed_availability: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "available": 0})
        self.specialist_availability: Dict[str, Dict[str, Any]] = {}
        self.department_queues: Dict[str, int] = defaultdict(int)
        self.equipment_availability: Dict[str, Dict[str, Any]] = {}
        self.historical_capacity: deque = deque(maxlen=288)  # 48 hours of 10-minute intervals
        self.last_updated: datetime = datetime.now()
        
    def update_bed_status(self, department: str, total_beds: int, available_beds: int):
        """Update bed availability with utilization tracking"""
        self.bed_availability[department] = {
            "total": total_beds,
            "available": available_beds,
            "utilization": (total_beds - available_beds) / total_beds if total_beds > 0 else 0,
            "last_updated": datetime.now()
        }
        self._record_capacity_snapshot()
    
    def update_specialist_status(self, specialist: str, available: bool, 
                               estimated_free_time: Optional[datetime] = None):
        """Enhanced specialist tracking"""
        self.specialist_availability[specialist] = {
            "available": available,
            "estimated_free": estimated_free_time,
            "last_updated": datetime.now()
        }
    
    def update_equipment_status(self, equipment_type: str, total_units: int, 
                              available_units: int, maintenance_scheduled: int = 0):
        """Track equipment availability"""
        self.equipment_availability[equipment_type] = {
            "total": total_units,
            "available": available_units,
            "in_use": total_units - available_units - maintenance_scheduled,
            "maintenance": maintenance_scheduled,
            "utilization": (total_units - available_units) / total_units if total_units > 0 else 0
        }
    
    def _record_capacity_snapshot(self):
        """Record capacity snapshot for trend analysis"""
        snapshot = {
            "timestamp": datetime.now(),
            "overall_utilization": self.get_overall_utilization(),
            "bottlenecks": len(self.get_bottlenecks())
        }
        self.historical_capacity.append(snapshot)
    
    def get_overall_utilization(self) -> float:
        """Calculate overall ED utilization"""
        if not self.bed_availability:
            return 0.0
        
        total_beds = sum(dept["total"] for dept in self.bed_availability.values())
        available_beds = sum(dept["available"] for dept in self.bed_availability.values())
        
        return (total_beds - available_beds) / total_beds if total_beds > 0 else 0.0
    
    def get_bottlenecks(self) -> List[Dict[str, Any]]:
        """Advanced bottleneck detection with severity scoring"""
        bottlenecks = []
        
        # Bed bottlenecks
        for dept, status in self.bed_availability.items():
            if status["available"] == 0:
                bottlenecks.append({
                    "type": "bed_shortage",
                    "department": dept,
                    "severity": "critical",
                    "message": f"No {dept} beds available",
                    "impact": "high"
                })
            elif status["utilization"] > 0.9:
                bottlenecks.append({
                    "type": "bed_shortage",
                    "department": dept,
                    "severity": "warning",
                    "message": f"{dept} at {status['utilization']:.0%} capacity",
                    "impact": "medium"
                })
        
        # Specialist bottlenecks
        for specialist, status in self.specialist_availability.items():
            if not status["available"]:
                severity = "critical" if specialist in ["cardiology", "trauma_surgery"] else "warning"
                bottlenecks.append({
                    "type": "specialist_unavailable",
                    "specialist": specialist,
                    "severity": severity,
                    "message": f"{specialist} unavailable",
                    "estimated_free": status.get("estimated_free"),
                    "impact": "high" if severity == "critical" else "medium"
                })
        
        # Equipment bottlenecks
        for equipment, status in self.equipment_availability.items():
            if status["available"] == 0:
                bottlenecks.append({
                    "type": "equipment_unavailable",
                    "equipment": equipment,
                    "severity": "warning",
                    "message": f"No {equipment} available",
                    "impact": "medium"
                })
        
        return bottlenecks
    
    def predict_capacity_issues(self, hours_ahead: int = 4) -> List[Dict[str, Any]]:
        """Predict potential capacity issues"""
        if len(self.historical_capacity) < 12:  # Need at least 2 hours of data
            return []
        
        # Simple trend analysis
        recent_utilization = [snapshot["overall_utilization"] for snapshot in list(self.historical_capacity)[-12:]]
        trend = (recent_utilization[-1] - recent_utilization[0]) / len(recent_utilization)
        
        predictions = []
        if trend > 0.02:  # Increasing utilization trend
            predicted_utilization = recent_utilization[-1] + (trend * hours_ahead * 6)  # 6 intervals per hour
            if predicted_utilization > 0.95:
                predictions.append({
                    "type": "capacity_overflow",
                    "severity": "warning",
                    "message": f"Capacity may reach {predicted_utilization:.0%} in {hours_ahead} hours",
                    "recommended_action": "Consider discharge planning and transfer preparation"
                })
        
        return predictions
    
    def get_capacity_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive capacity dashboard"""
        return {
            "overall_utilization": self.get_overall_utilization(),
            "bed_status": dict(self.bed_availability),
            "specialist_status": dict(self.specialist_availability),
            "equipment_status": dict(self.equipment_availability),
            "bottlenecks": self.get_bottlenecks(),
            "predictions": self.predict_capacity_issues(),
            "last_updated": self.last_updated.isoformat()
        }

# Communication system for real-time coordination
class CommunicationHub:
    """Real-time communication and notification system"""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.message_templates = self._initialize_templates()
        self.communication_log: List[Dict[str, Any]] = []
    
    def _initialize_templates(self) -> Dict[str, str]:
        """Initialize communication templates"""
        return {
            "critical_result": "CRITICAL RESULT: {test} for {patient_id} - {result}. Immediate attention required.",
            "diagnostic_complete": "Diagnostic workup complete for {patient_id}. Ready for next stage.",
            "handoff_ready": "Patient {patient_id} ready for handoff to {department}. Package prepared by {staff}.",
            "capacity_alert": "CAPACITY ALERT: {department} at {utilization}% capacity. {available} beds remaining.",
            "protocol_violation": "PROTOCOL ALERT: {violation} for {patient_id}. Clinical review needed.",
            "overdue_diagnostic": "OVERDUE: {test} for {patient_id} ordered {time_ago} ago. Follow-up needed."
        }
    
    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to event notifications"""
        self.subscribers[event_type].append(callback)
    
    def publish(self, event_type: str, data: Dict[str, Any]):
        """Publish event to subscribers"""
        for callback in self.subscribers.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in callback for {event_type}: {e}")
        
        # Log communication
        self.communication_log.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        })
    
    def send_notification(self, template_key: str, recipients: List[str], **kwargs) -> str:
        """Send formatted notification"""
        if template_key not in self.message_templates:
            logger.error(f"Unknown template: {template_key}")
            return ""
        
        message = self.message_templates[template_key].format(**kwargs)
        
        notification_data = {
            "message": message,
            "recipients": recipients,
            "template": template_key,
            "timestamp": datetime.now().isoformat()
        }
        
        self.publish("notification_sent", notification_data)
        return message
    
    def get_communication_summary(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get communication activity summary"""
        cutoff = datetime.now() - timedelta(hours=hours_back)
        
        recent_communications = [
            comm for comm in self.communication_log 
            if datetime.fromisoformat(comm["timestamp"]) > cutoff
        ]
        
        return {
            "total_communications": len(recent_communications),
            "by_event_type": defaultdict(int),
            "recent_communications": recent_communications[-10:]  # Last 10
        }

class EnhancedEDCoordinator:
    """Complete ED coordination system with advanced features"""
    
    def __init__(self):
        self.patients: Dict[str, PatientWorkflow] = {}
        self.capacity: EnhancedCapacityMonitor = EnhancedCapacityMonitor()
        self.protocol_engine: ClinicalProtocolEngine = ClinicalProtocolEngine()
        self.communication: CommunicationHub = CommunicationHub()
        self.active_alerts: Dict[str, ClinicalAlert] = {}
        
        # Setup communication subscribers
        self._setup_communication_handlers()
    
    def _setup_communication_handlers(self):
        """Setup event handlers for communication"""
        self.communication.subscribe("critical_result", self._handle_critical_result)
        self.communication.subscribe("capacity_alert", self._handle_capacity_alert)
        self.communication.subscribe("protocol_violation", self._handle_protocol_violation)
    
    def _handle_critical_result(self, data: Dict[str, Any]):
        """Handle critical diagnostic result"""
        logger.critical(f"Critical result notification: {data}")
        # Additional critical result handling logic would go here
    
    def _handle_capacity_alert(self, data: Dict[str, Any]):
        """Handle capacity alerts"""
        logger.warning(f"Capacity alert: {data}")
        # Capacity management logic would go here
    
    def _handle_protocol_violation(self, data: Dict[str, Any]):
        """Handle protocol violations"""
        logger.warning(f"Protocol violation: {data}")
        # Clinical escalation logic would go here
    
    def register_patient(self, patient_id: str, chief_complaint: str, 
                        ems_notes: str = "", vitals: Dict[str, Any] = None,
                        age: int = None, gender: str = None,
                        comorbidities: List[str] = None) -> PatientWorkflow:
        """Enhanced patient registration"""
        # Create vital signs if provided
        vital_signs = None
        if vitals:
            vital_signs = VitalSigns(
                timestamp=datetime.now(),
                systolic_bp=vitals.get("sbp"),
                diastolic_bp=vitals.get("dbp"), 
                heart_rate=vitals.get("hr"),
                respiratory_rate=vitals.get("rr"),
                temperature=vitals.get("temp"),
                oxygen_saturation=vitals.get("spo2"),
                pain_score=vitals.get("pain")
            )
        
        # Create patient workflow
        workflow = PatientWorkflow(
            patient_id=patient_id,
            arrival_time=datetime.now(),
            chief_complaint=chief_complaint,
            ems_notes=ems_notes,
            age=age,
            gender=gender,
            comorbidities=comorbidities or []
        )
        
        if vital_signs:
            workflow.add_vital_signs(vital_signs)
        
        self.patients[patient_id] = workflow
        
        # Send registration notification
        self.communication.send_notification(
            "patient_registered",
            ["charge_nurse", "attending"],
            patient_id=patient_id,
            chief_complaint=chief_complaint
        )
        
        logger.info(f"Patient {patient_id} registered: {chief_complaint}")
        return workflow
    
    def suggest_diagnostic_pathway(self, patient_id: str) -> List[Dict[str, Any]]:
        """Enhanced diagnostic pathway suggestions"""
        if patient_id not in self.patients:
            return []
        
        patient = self.patients[patient_id]
        return self.protocol_engine.suggest_diagnostic_pathway(patient)
    
    def order_diagnostic(self, patient_id: str, test_type: str, ordered_by: str,
                        priority: str = "routine") -> bool:
        """Order diagnostic with protocol validation"""
        if patient_id not in self.patients:
            logger.error(f"Patient {patient_id} not found")
            return False
        
        patient = self.patients[patient_id]
        
        # Get test configuration from protocol
        suggestions = self.suggest_diagnostic_pathway(patient_id)
        test_config = next((s for s in suggestions if s["test"] == test_type), None)
        
        if test_config:
            patient.add_diagnostic_order(
                test_type=test_type,
                ordered_by=ordered_by,
                expected_minutes=test_config["expected_minutes"],
                priority=test_config["priority"],
                department=test_config["department"]
            )
        else:
            # Default configuration for non-protocol tests
            patient.add_diagnostic_order(
                test_type=test_type,
                ordered_by=ordered_by,
                priority=priority
            )
        
        logger.info(f"Diagnostic {test_type} ordered for {patient_id}")
        return True
    
    def update_diagnostic_result(self, patient_id: str, test_type: str, 
                               result_summary: str, critical: bool = False,
                               result_data: Dict[str, Any] = None) -> List[str]:
        """Process diagnostic result with notifications"""
        if patient_id not in self.patients:
            return []
        
        patient = self.patients[patient_id]
        success = patient.update_diagnostic_status(
            test_type, DiagnosticStatus.COMPLETED, 
            result_summary, critical, result_data
        )
        
        if not success:
            return []
        
        notifications = []
        
        # Handle critical results
        if critical:
            self.communication.send_notification(
                "critical_result",
                ["attending", "charge_nurse"],
                test=test_type,
                patient_id=patient_id,
                result=result_summary
            )
            notifications.append(f"CRITICAL: {test_type} result for {patient_id}")
        
        # Check if diagnostic workup is complete
        pending = patient.get_pending_diagnostics()
        if not pending:
            patient.advance_stage(HandoffStage.DIAGNOSIS_CLEAR)
            self.communication.send_notification(
                "diagnostic_complete",
                ["attending"],
                patient_id=patient_id
            )
            notifications.append(f"Diagnostic workup complete for {patient_id}")
        
        # Check protocol compliance
        compliance = self.protocol_engine.check_protocol_compliance(patient)
        if not compliance["compliant"]:
            for violation in compliance["violations"]:
                self.communication.send_notification(
                    "protocol_violation",
                    ["attending", "charge_nurse"],
                    violation=violation,
                    patient_id=patient_id
                )
        
        return notifications
    
    def get_comprehensive_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive operational dashboard"""
        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "patient_summary": self._get_patient_summary(),
            "workflow_metrics": self._get_workflow_metrics(),
            "capacity_status": self.capacity.get_capacity_dashboard(),
            "active_alerts": self._get_active_alerts_summary(),
            "protocol_compliance": self._get_protocol_compliance_summary(),
            "communication_summary": self.communication.get_communication_summary(),
            "performance_indicators": self._get_performance_indicators()
        }
        
        return dashboard
    
    def _get_patient_summary(self) -> Dict[str, Any]:
        """Get patient census and flow summary"""
        summary = {
            "total_patients": len(self.patients),
            "by_stage": defaultdict(int),
            "by_protocol": defaultdict(int),
            "avg_los": None,
            "pending_transfers": 0,
            "ready_for_discharge": 0
        }
        
        los_times = []
        for patient in self.patients.values():
            summary["by_stage"][patient.current_stage.value] += 1
            
            if patient.clinical_protocol:
                summary["by_protocol"][patient.clinical_protocol.value] += 1
            
            los = datetime.now() - patient.arrival_time
            los_times.append(los.total_seconds() / 3600)  # hours
            
            if patient.current_stage == HandoffStage.READY_TRANSFER:
                summary["pending_transfers"] += 1
            elif patient.is_handoff_ready():
                summary["ready_for_discharge"] += 1
        
        if los_times:
            summary["avg_los"] = sum(los_times) / len(los_times)
        
        return dict(summary)
    
    def _get_workflow_metrics(self) -> Dict[str, Any]:
        """Calculate workflow performance metrics"""
        metrics = {
            "pending_diagnostics": 0,
            "overdue_diagnostics": 0,
            "avg_diagnostic_turnaround": None,
            "handoff_completion_rate": 0
        }
        
        turnaround_times = []
        completed_handoffs = 0
        total_ready_for_handoff = 0
        
        for patient in self.patients.values():
            metrics["pending_diagnostics"] += len(patient.get_pending_diagnostics())
            metrics["overdue_diagnostics"] += len(patient.get_overdue_diagnostics())
            
            # Calculate diagnostic turnaround times
            for order in patient.diagnostics.values():
                if order.status == DiagnosticStatus.COMPLETED and order.result_available_at:
                    turnaround = order.result_available_at - order.ordered_at
                    turnaround_times.append(turnaround.total_seconds() / 60)  # minutes
            
            # Handoff metrics
            if patient.current_stage in [HandoffStage.READY_TRANSFER, HandoffStage.TRANSFERRED]:
                total_ready_for_handoff += 1
                if patient.handoff_package.complete:
                    completed_handoffs += 1
        
        if turnaround_times:
            metrics["avg_diagnostic_turnaround"] = sum(turnaround_times) / len(turnaround_times)
        
        if total_ready_for_handoff > 0:
            metrics["handoff_completion_rate"] = completed_handoffs / total_ready_for_handoff
        
        return metrics
    
    def _get_active_alerts_summary(self) -> Dict[str, Any]:
        """Summarize active alerts across all patients"""
        all_alerts = []
        for patient in self.patients.values():
            all_alerts.extend(patient.alerts)
        
        return {
            "total_alerts": len(all_alerts),
            "by_severity": {
                severity.value: len([a for a in all_alerts if a.severity == severity])
                for severity in AlertSeverity
            },
            "unacknowledged": len([a for a in all_alerts if not a.acknowledged]),
            "critical_unresolved": len([a for a in all_alerts 
                                     if a.severity == AlertSeverity.CRITICAL and not a.resolved])
        }
    
    def _get_protocol_compliance_summary(self) -> Dict[str, Any]:
        """Check protocol compliance across all patients"""
        compliance_data = {
            "total_patients": 0,
            "compliant_patients": 0,
            "violations": []
        }
        
        for patient in self.patients.values():
            if patient.clinical_protocol:
                compliance_data["total_patients"] += 1
                compliance = self.protocol_engine.check_protocol_compliance(patient)
                if compliance["compliant"]:
                    compliance_data["compliant_patients"] += 1
                else:
                    compliance_data["violations"].extend([
                        {"patient_id": patient.patient_id, "violation": v}
                        for v in compliance["violations"]
                    ])
        
        compliance_rate = 0
        if compliance_data["total_patients"] > 0:
            compliance_rate = compliance_data["compliant_patients"] / compliance_data["total_patients"]
        
        compliance_data["compliance_rate"] = compliance_rate
        return compliance_data
    
    def _get_performance_indicators(self) -> Dict[str, Any]:
        """Calculate key performance indicators"""
        return {
            "throughput": len([p for p in self.patients.values() 
                             if p.current_stage in [HandoffStage.TRANSFERRED, HandoffStage.DISCHARGED]]),
            "capacity_utilization": self.capacity.get_overall_utilization(),
            "bottleneck_count": len(self.capacity.get_bottlenecks()),
            "critical_alert_response_time": None,  # Would need alert response tracking
            "staff_workload_balance": None  # Would need staff tracking
        }
    
    def generate_handoff_report(self, patient_id: str) -> Dict[str, Any]:
        """Generate comprehensive handoff report"""
        if patient_id not in self.patients:
            return {"error": "Patient not found"}
        
        patient = self.patients[patient_id]
        
        return {
            "patient_info": {
                "id": patient_id,
                "age": patient.age,
                "gender": patient.gender,
                "chief_complaint": patient.chief_complaint,
                "arrival_time": patient.arrival_time.isoformat(),
                "total_los": str(datetime.now() - patient.arrival_time),
                "comorbidities": patient.comorbidities
            },
            "clinical_summary": {
                "current_stage": patient.current_stage.value,
                "protocol": patient.clinical_protocol.value if patient.clinical_protocol else None,
                "latest_vitals": asdict(patient.get_latest_vitals()) if patient.get_latest_vitals() else None,
                "diagnostics_completed": [
                    {"test": test, "result": order.result_summary, "critical": order.critical_result}
                    for test, order in patient.diagnostics.items()
                    if order.status == DiagnosticStatus.COMPLETED
                ],
                "pending_diagnostics": patient.get_pending_diagnostics()
            },
            "handoff_package": asdict(patient.handoff_package),
            "alerts": [asdict(alert) for alert in patient.get_critical_alerts()],
            "ready_for_handoff": patient.is_handoff_ready(),
            "estimated_completion": patient.estimate_completion_time().isoformat() if patient.estimate_completion_time() else None
        }

# Factory function for system initialization
def create_enhanced_coordination_system() -> EnhancedEDCoordinator:
    """Initialize the enhanced ED coordination system"""
    coordinator = EnhancedEDCoordinator()
    
    # Initialize capacity monitoring
    coordinator.capacity.update_bed_status("general_medicine", 20, 5)
    coordinator.capacity.update_bed_status("cardiology", 8, 2)
    coordinator.capacity.update_bed_status("icu", 6, 1)
    
    coordinator.capacity.update_specialist_status("cardiology", True)
    coordinator.capacity.update_specialist_status("radiology", True)
    coordinator.capacity.update_specialist_status("surgery", False, 
                                                 datetime.now() + timedelta(hours=2))
    
    coordinator.capacity.update_equipment_status("CT_scanner", 2, 1)
    coordinator.capacity.update_equipment_status("MRI", 1, 0, 1)
    
    logger.info("Enhanced ED Coordination System initialized")
    return coordinator

# Example usage and testing
def demonstrate_system():
    """Demonstrate the enhanced system capabilities"""
    coordinator = create_enhanced_coordination_system()
    
    # Register a patient
    patient = coordinator.register_patient(
        "ED-12345",
        "chest pain",
        "EMS: 65yo M, chest pain x2h, diaphoretic, HR 95",
        vitals={"sbp": 140, "dbp": 80, "hr": 95, "spo2": 96, "pain": 8},
        age=65,
        gender="M",
        comorbidities=["diabetes", "hypertension"]
    )
    
    # Get diagnostic suggestions
    suggestions = coordinator.suggest_diagnostic_pathway("ED-12345")
    print("Diagnostic suggestions:", suggestions)
    
    # Order diagnostics
    for suggestion in suggestions:
        coordinator.order_diagnostic("ED-12345", suggestion["test"], "Dr. Smith", suggestion["priority"])
    
    # Simulate result
    coordinator.update_diagnostic_result(
        "ED-12345", "troponin_serial", 
        "Elevated troponin: 0.8 ng/mL", 
        critical=True
    )
    
    # Generate dashboard
    dashboard = coordinator.get_comprehensive_dashboard()
    print("Dashboard summary:", {k: v for k, v in dashboard.items() if k != "communication_summary"})
    
    return coordinator

if __name__ == "__main__":
    coordinator = demonstrate_system()
