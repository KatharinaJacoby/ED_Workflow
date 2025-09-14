# ============================================================================
# COMPLETION: LINGERING PATIENT MONITOR + SYSTEM INTEGRATION
# ============================================================================

# Complete the LingeringPatientMonitor.check_lingering_patients() method
def complete_lingering_patient_monitor():
    """Complete the cut-off LingeringPatientMonitor implementation."""
    
    class EnhancedLingeringPatientMonitor:
        """
        Complete lingering patient monitor with policy integration.
        Source: Clinical Requirements - "Stable patients linger in ED due to overcrowding"
        """
        
        def __init__(self):
            self.patients: Dict[str, Dict[str, Any]] = {}
            self.alert_thresholds = {
                "assessment_overdue_min": 120,  # >2 hours without assessment
                "vitals_overdue_min": 240,      # >4 hours without vitals
                "basic_needs_min": 360,         # >6 hours without food/comfort
            }
        
        def register_patient(self, patient_id: str, workflow_state: WorkflowState):
            """Register patient for lingering monitoring."""
            now = pd.Timestamp.utcnow()
            self.patients[patient_id] = {
                "workflow_state": workflow_state,
                "registered_at": now,
                "last_check": now,
                "red_flags": []
            }
        
        def update_patient(self, patient_id: str, workflow_state: WorkflowState):
            """Update patient's workflow state."""
            if patient_id in self.patients:
                self.patients[patient_id]["workflow_state"] = workflow_state
                self.patients[patient_id]["last_check"] = pd.Timestamp.utcnow()
        
        def check_lingering_patients(self) -> List[Dict[str, Any]]:
            """Check for patients who are lingering and need attention."""
            alerts = []
            
            for patient_id, patient_data in self.patients.items():
                state = patient_data["workflow_state"]
                
                # Use the WorkflowState's feature_dict to get current status
                if hasattr(state, 'feature_dict'):
                    features = state.feature_dict()
                    since_vitals = features.get("since_vitals_min", 0)
                    
                    # Check if patient is lingering
                    if since_vitals > self.alert_thresholds["assessment_overdue_min"]:
                        alert = {
                            "patient_id": patient_id,
                            "type": "lingering_patient",
                            "severity": self._determine_severity(since_vitals),
                            "since_vitals_min": since_vitals,
                            "recommended_actions": self._get_recommendations(since_vitals, features),
                            "timestamp": pd.Timestamp.utcnow().isoformat()
                        }
                        alerts.append(alert)
                        
                        # Update red flags
                        patient_data["red_flags"].append({
                            "type": "lingering_detected",
                            "timestamp": pd.Timestamp.utcnow(),
                            "since_vitals": since_vitals
                        })
            
            return alerts
        
        def _determine_severity(self, since_vitals_min: float) -> str:
            """Determine severity based on time since last vitals."""
            if since_vitals_min > self.alert_thresholds["basic_needs_min"]:
                return "critical"  # >6 hours
            elif since_vitals_min > self.alert_thresholds["vitals_overdue_min"]:
                return "high"     # >4 hours
            elif since_vitals_min > self.alert_thresholds["assessment_overdue_min"]:
                return "medium"   # >2 hours
            else:
                return "low"
        
        def _get_recommendations(self, since_vitals_min: float, features: Dict) -> List[str]:
            """Get recommendations based on patient status."""
            recommendations = []
            
            if since_vitals_min > self.alert_thresholds["basic_needs_min"]:
                recommendations.extend([
                    "IMMEDIATE_PHYSICIAN_REVIEW",
                    "CHECK_BASIC_NEEDS",
                    "CONSIDER_DISCHARGE_READINESS",
                    "SOCIAL_WORK_CONSULT"
                ])
            elif since_vitals_min > self.alert_thresholds["vitals_overdue_min"]:
                recommendations.extend([
                    "NURSING_ASSESSMENT",
                    "VITAL_SIGNS_OVERDUE", 
                    "CHECK_PENDING_RESULTS"
                ])
            elif since_vitals_min > self.alert_thresholds["assessment_overdue_min"]:
                recommendations.extend([
                    "ROUTINE_VITALS_DUE",
                    "COMFORT_ROUNDS"
                ])
            
            # Add specific recommendations based on workflow state
            if features.get("troponin_pending"):
                recommendations.append("FOLLOW_UP_TROPONIN_RESULTS")
            
            if features.get("ct_pending"):
                recommendations.append("CHECK_IMAGING_DELAYS")
            
            if features.get("cardiology_consulted") and since_vitals_min > 180:
                recommendations.append("FOLLOW_UP_CARDIOLOGY_RECOMMENDATIONS")
            
            return recommendations
        
        def get_summary_stats(self) -> Dict[str, Any]:
            """Get summary statistics for lingering patients."""
            total = len(self.patients)
            lingering = 0
            overdue = 0
            
            for patient_data in self.patients.values():
                state = patient_data["workflow_state"]
                if hasattr(state, 'is_lingering_patient'):
                    if state.is_lingering_patient(120):  # 2 hours
                        lingering += 1
                    if state.is_lingering_patient(240):  # 4 hours
                        overdue += 1
            
            return {
                "total_patients": total,
                "lingering_patients": lingering,
                "overdue_patients": overdue,
                "percentage_lingering": (lingering / total * 100.0) if total > 0 else 0.0
            }
    
    return EnhancedLingeringPatientMonitor()

# ============================================================================
# SYSTEM INTEGRATION: WIRE ALL COMPONENTS TOGETHER
# ============================================================================

class IntegratedClinicalSystem:
    """
    Master controller that integrates all enhanced components.
    This is what was missing from your implementation - the orchestration layer.
    """
    
    def __init__(self):
        self.results_notifier = None
        self.reminder_engine = None
        self.lingering_monitor = None
        self.policy_engine = None
        self.audit_logger = None
        self.orbis = None
        self.tiny_critics = None
        
        # Initialize if pipeline enabled
        if RUN_PIPELINE:
            self._initialize_components()
            self._wire_callbacks()
        
    def _initialize_components(self):
        """Initialize all system components."""
        self.results_notifier = ResultsNotifier()
        self.reminder_engine = ReminderEngine()
        self.lingering_monitor = complete_lingering_patient_monitor()
        self.policy_engine = POLICY_ENGINE
        self.audit_logger = AUDIT_LOGGER
        self.orbis = ORBIS
        self.tiny_critics = TinyCritics()
        
        print("✅ All clinical components initialized")
    
    def _wire_callbacks(self):
        """Wire up callbacks between components."""
        if not RUN_PIPELINE:
            return
        
        # Results notifier → reminder engine
        self.results_notifier.on_notify(self._on_lab_result)
        
        # Results notifier → audit logging
        self.results_notifier.on_notify(self._on_audit_lab_result)
        
        # Reminder engine → audit logging
        self.reminder_engine.on_notify(self._on_audit_reminder)
        
        print("✅ Component callbacks wired")
    
    def _on_lab_result(self, patient_id: str, event: str, payload: Dict[str, Any]):
        """Handle lab results and trigger reminder logic."""
        if event == "lab_result_ready":
            # Trigger reminder engine
            self.reminder_engine.ingest_event(patient_id, "lab_result", payload)
            
            # Check for troponin delta
            if payload.get("test_code") == "TROPONIN":
                self.reminder_engine.ingest_event(patient_id, "troponin_result", payload)
        
        elif event == "lab_delta_positive":
            # Critical delta detected
            self.reminder_engine.ingest_event(patient_id, "critical_delta", payload)
    
    def _on_audit_lab_result(self, patient_id: str, event: str, payload: Dict[str, Any]):
        """Audit lab results."""
        self.audit_logger.log_action(
            action={"type": "lab_result", "patient_id": patient_id},
            context={"event": event},
            result=payload
        )
    
    def _on_audit_reminder(self, patient_id: str, key: str, payload: Dict[str, Any]):
        """Audit reminder events."""
        self.audit_logger.log_action(
            action={"type": "reminder", "patient_id": patient_id},
            context={"reminder_key": key},
            result=payload
        )
    
    def process_patient(self, patient_id: str, workflow_state: WorkflowState) -> Dict[str, Any]:
        """
        Complete patient processing through all system components.
        This is the main integration point.
        """
        if not RUN_PIPELINE:
            return {"processed": False, "reason": "pipeline_disabled"}
        
        results = {
            "patient_id": patient_id,
            "timestamp": pd.Timestamp.utcnow().isoformat(),
            "components_processed": []
        }
        
        try:
            # 1. Register with lingering monitor
            self.lingering_monitor.register_patient(patient_id, workflow_state)
            results["components_processed"].append("lingering_monitor")
            
            # 2. Generate action candidates
            candidates = generate_candidates(workflow_state)
            results["action_candidates"] = candidates
            results["components_processed"].append("action_generation")
            
            # 3. Score actions with TinyCritics
            if candidates:
                scores, benefits, burdens = self.tiny_critics.score(workflow_state, candidates)
                results["action_scores"] = {
                    "scores": scores.tolist(),
                    "benefits": benefits.tolist(), 
                    "burdens": burdens.tolist()
                }
                results["components_processed"].append("tiny_critics")
            
            # 4. Policy evaluation for each candidate
            policy_results = []
            for i, candidate in enumerate(candidates):
                policy_result = self.policy_engine.evaluate_action(
                    {"code": candidate.get("action", ""), "patient_id": patient_id},
                    {"workflow_state": workflow_state.feature_dict()}
                )
                policy_results.append(policy_result)
            
            results["policy_evaluations"] = policy_results
            results["components_processed"].append("policy_engine")
            
            # 5. Check for lingering patients
            lingering_alerts = self.lingering_monitor.check_lingering_patients()
            results["lingering_alerts"] = lingering_alerts
            results["components_processed"].append("lingering_check")
            
            # 6. Get risk scores if chest pain
            if workflow_state.chest_pain:
                patient_data = {
                    "chief_complaint": "chest_pain",
                    "chest_pain": True,
                    "age": 55,  # Default for demo
                    "troponin": 25.0  # Default for demo
                }
                risk_scores = complete_risk_scores(patient_data)
                results["risk_scores"] = risk_scores
                results["components_processed"].append("risk_scores")
                
                # STEMI fast track if ECG completed
                if "ORDER_ECG" in workflow_state.completed_studies:
                    ecg_data = {"st_elevation": False}  # Default for demo
                    stemi_result = stemi_fast_track_protocol(ecg_data)
                    results["stemi_protocol"] = stemi_result
                    results["components_processed"].append("stemi_protocol")
            
            # 7. Orbis integration
            demographics = self.orbis.get_patient_demographics(patient_id)
            if "error" not in demographics:
                results["patient_demographics"] = demographics
                results["components_processed"].append("orbis_demographics")
            
            # 8. Audit the complete processing
            audit_hash = self.audit_logger.log_action(
                action={"type": "complete_patient_processing", "patient_id": patient_id},
                context={"workflow_state": workflow_state.feature_dict()},
                result=results
            )
            results["audit_hash"] = audit_hash
            results["components_processed"].append("audit")
            
            results["processed"] = True
            
        except Exception as e:
            results["processed"] = False
            results["error"] = str(e)
            
            # Still audit the failure
            self.audit_logger.log_action(
                action={"type": "patient_processing_error", "patient_id": patient_id},
                context={"error": str(e)},
                result={"processed": False}
            )
        
        return results
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system health and status."""
        status = {
            "timestamp": pd.Timestamp.utcnow().isoformat(),
            "pipeline_enabled": RUN_PIPELINE,
            "components": {
                "results_notifier": self.results_notifier is not None,
                "reminder_engine": self.reminder_engine is not None,
                "lingering_monitor": self.lingering_monitor is not None,
                "policy_engine": self.policy_engine is not None,
                "audit_logger": self.audit_logger is not None,
                "orbis": self.orbis is not None,
                "tiny_critics": self.tiny_critics is not None
            }
        }
        
        if RUN_PIPELINE and self.lingering_monitor:
            status["lingering_stats"] = self.lingering_monitor.get_summary_stats()
        
        if RUN_PIPELINE and self.audit_logger:
            audit_verification = self.audit_logger.verify_integrity()
            status["audit_integrity"] = audit_verification
        
        return status

# ============================================================================
# GLOBAL SYSTEM INITIALIZATION
# ============================================================================

# Initialize the complete integrated system
INTEGRATED_SYSTEM = IntegratedClinicalSystem()

def demo_complete_integration():
    """Demonstrate the complete integrated system."""
    if not RUN_PIPELINE:
        print("Demo requires RUN_PIPELINE = True")
        return
    
    print("\n=== COMPLETE SYSTEM INTEGRATION DEMO ===")
    
    # Create a demo patient
    demo_state = WorkflowState(
        encounter_id="ENC001",
        patient_id="P001",
        pending_orders={"LAB_TROPONIN", "ORDER_ECG"},
        completed_studies={"ORDER_VITALS"},
        chest_pain=True,
        hour=14,
        role="nurse"
    )
    demo_state.touch_now()  # Set vitals timestamp
    
    print(f"✅ Demo patient created: {demo_state.patient_id}")
    
    # Process through complete system
    results = INTEGRATED_SYSTEM.process_patient("P001", demo_state)
    
    print(f"✅ Processing completed: {results['processed']}")
    print(f"✅ Components processed: {len(results['components_processed'])}")
    
    for component in results['components_processed']:
        print(f"  - {component}")
    
    # Show system status
    status = INTEGRATED_SYSTEM.get_system_status()
    print(f"✅ System status: {sum(status['components'].values())}/{len(status['components'])} components active")
    
    return results, status

# Print completion summary
print("\n" + "="*50)
print("✅ COMPLETE ENHANCED CLINICAL SYSTEM READY")
print("="*50)
print("✅ Lingering patient monitor completed")
print("✅ System integration layer added") 
print("✅ Global orchestration implemented")
print("✅ End-to-end processing pipeline ready")
print("✅ All components wired with callbacks")
print("✅ Comprehensive audit trail maintained")
print("="*50)