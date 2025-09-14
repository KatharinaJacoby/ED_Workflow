# ED Handoff Demonstration - Complete Clinical Workflow
# Showing realistic patient journey from arrival to handoff

from datetime import datetime, timedelta
import json
from ed_coordinator_complete import *

def create_realistic_handoff_scenario():
    """Create a complete handoff scenario with a realistic patient"""
    
    print("=== ED COORDINATOR HANDOFF DEMONSTRATION ===\n")
    
    # Initialize the system
    coordinator = create_enhanced_coordination_system()
    print("✓ ED Coordination System initialized")
    
    # === PATIENT ARRIVAL ===
    print("\n📋 PATIENT ARRIVAL")
    print("-" * 50)
    
    patient = coordinator.register_patient(
        patient_id="ED-2024-0892",
        chief_complaint="chest pain and shortness of breath",
        ems_notes="67yo F brought by EMS. Chest pain started 3 hours ago while gardening. Pain 8/10, radiating to left arm. Diaphoretic, mildly dyspneic. PMH: DM, HTN, hyperlipidemia. Takes metformin, lisinopril, atorvastatin.",
        vitals={
            "sbp": 156, "dbp": 89, "hr": 102, "rr": 22, 
            "spo2": 94, "temp": 98.2, "pain": 8
        },
        age=67,
        gender="F",
        comorbidities=["diabetes_type2", "hypertension", "hyperlipidemia"]
    )
    
    print(f"Patient {patient.patient_id} registered:")
    print(f"  Chief Complaint: {patient.chief_complaint}")
    print(f"  Age/Gender: {patient.age}yo {patient.gender}")
    print(f"  Arrival Time: {patient.arrival_time.strftime('%H:%M')}")
    print(f"  Initial Vitals: BP {patient.vital_signs_history[0].systolic_bp}/{patient.vital_signs_history[0].diastolic_bp}, HR {patient.vital_signs_history[0].heart_rate}")
    
    # === TRIAGE COMPLETION ===
    print("\n🏥 TRIAGE & INITIAL ASSESSMENT")
    print("-" * 50)
    
    # Add triage notes
    patient.triage_notes = "ESI Level 2. Chest pain with cardiac risk factors. Appears uncomfortable, diaphoretic. Lungs clear, no acute distress but c/o ongoing chest pressure."
    patient.advance_stage(HandoffStage.TRIAGE_COMPLETE, "Nurse Johnson")
    
    print("✓ Triage completed - ESI Level 2")
    print("✓ Bed assigned: Bay 3")
    patient.bed_assigned = "Bay 3"
    patient.staff_assigned.add("Dr. Martinez")
    patient.staff_assigned.add("Nurse Johnson")
    
    # === DIAGNOSTIC WORKUP ===
    print("\n🔬 DIAGNOSTIC WORKUP")
    print("-" * 50)
    
    # Get protocol-based diagnostic suggestions
    suggestions = coordinator.suggest_diagnostic_pathway("ED-2024-0892")
    print("Protocol-based diagnostic pathway (Chest Pain):")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"  {i}. {suggestion['test']} - {suggestion['priority']} priority ({suggestion['expected_minutes']} min)")
    
    # Order diagnostics following protocol
    print("\nOrdering diagnostics...")
    coordinator.order_diagnostic("ED-2024-0892", "ECG", "Dr. Martinez", "stat")
    coordinator.order_diagnostic("ED-2024-0892", "troponin_serial", "Dr. Martinez", "urgent") 
    coordinator.order_diagnostic("ED-2024-0892", "chest_xray", "Dr. Martinez", "urgent")
    coordinator.order_diagnostic("ED-2024-0892", "d_dimer", "Dr. Martinez", "routine")
    
    # Additional orders based on clinical assessment
    coordinator.order_diagnostic("ED-2024-0892", "BNP", "Dr. Martinez", "routine")
    coordinator.order_diagnostic("ED-2024-0892", "basic_metabolic", "Dr. Martinez", "routine")
    
    patient.advance_stage(HandoffStage.WORKUP_ACTIVE, "Dr. Martinez")
    print("✓ Diagnostic workup initiated - 6 tests ordered")
    
    # === SIMULATING DIAGNOSTIC RESULTS ===
    print("\n📊 DIAGNOSTIC RESULTS")
    print("-" * 50)
    
    # ECG result (immediate)
    coordinator.update_diagnostic_result(
        "ED-2024-0892", "ECG", 
        "Sinus tachycardia 102 bpm. ST depression in leads II, III, aVF. No acute ST elevation.", 
        critical=False,
        result_data={"rhythm": "sinus_tachycardia", "rate": 102, "st_changes": "depression_inferior"}
    )
    print("✓ ECG completed: ST depression in inferior leads")
    
    # Wait for other results (simulating time passage)
    print("⏱️  Awaiting lab results and imaging...")
    patient.advance_stage(HandoffStage.AWAITING_RESULTS, "Dr. Martinez")
    
    # Chest X-ray result
    coordinator.update_diagnostic_result(
        "ED-2024-0892", "chest_xray",
        "Clear lung fields. Normal cardiac silhouette. No acute cardiopulmonary process.",
        critical=False,
        result_data={"lungs": "clear", "heart": "normal_size", "acute_findings": "none"}
    )
    print("✓ Chest X-ray: Normal")
    
    # First troponin result
    coordinator.update_diagnostic_result(
        "ED-2024-0892", "troponin_serial",
        "Elevated troponin I: 0.12 ng/mL (normal <0.04). Consistent with myocardial injury.",
        critical=True,
        result_data={"value": 0.12, "units": "ng/mL", "normal_range": "<0.04", "interpretation": "elevated"}
    )
    print("🚨 CRITICAL: Elevated troponin - myocardial injury")
    
    # Other lab results
    coordinator.update_diagnostic_result(
        "ED-2024-0892", "d_dimer",
        "D-dimer: 0.8 mg/L (normal <0.5). Mildly elevated.",
        critical=False,
        result_data={"value": 0.8, "units": "mg/L", "normal_range": "<0.5"}
    )
    
    coordinator.update_diagnostic_result(
        "ED-2024-0892", "BNP",
        "BNP: 180 pg/mL (normal <100). Mildly elevated, suggests mild heart failure.",
        critical=False,
        result_data={"value": 180, "units": "pg/mL", "normal_range": "<100"}
    )
    
    coordinator.update_diagnostic_result(
        "ED-2024-0892", "basic_metabolic",
        "Normal electrolytes. Creatinine 1.1. Glucose 145 (mild elevation).",
        critical=False,
        result_data={"creatinine": 1.1, "glucose": 145, "electrolytes": "normal"}
    )
    
    print("✓ All diagnostic results completed")
    
    # === CLINICAL DECISION MAKING ===
    print("\n🩺 CLINICAL ASSESSMENT & TREATMENT")
    print("-" * 50)
    
    # Update patient to diagnosis clear stage
    patient.advance_stage(HandoffStage.DIAGNOSIS_CLEAR, "Dr. Martinez")
    
    # Add repeat vitals showing improvement
    improved_vitals = VitalSigns(
        timestamp=datetime.now(),
        systolic_bp=142, diastolic_bp=84, heart_rate=88, 
        respiratory_rate=18, oxygen_saturation=97, pain_score=4
    )
    patient.add_vital_signs(improved_vitals)
    print("✓ Repeat vitals: Improved (Pain 8→4, HR 102→88)")
    
    # Begin treatment
    patient.advance_stage(HandoffStage.TREATMENT_ACTIVE, "Dr. Martinez")
    print("✓ Treatment initiated:")
    print("  - Aspirin 324mg chewed")
    print("  - Atorvastatin 80mg")
    print("  - Metoprolol 25mg")
    print("  - Heparin per protocol")
    
    # === HANDOFF PACKAGE PREPARATION ===
    print("\n📋 HANDOFF PACKAGE PREPARATION")
    print("-" * 50)
    
    # Build comprehensive handoff package
    handoff = patient.handoff_package
    
    # Primary diagnosis
    handoff.diagnosis = "NSTEMI (Non-ST Elevation Myocardial Infarction)"
    handoff.differential_diagnoses = [
        "Unstable angina", 
        "Demand ischemia", 
        "Myocarditis"
    ]
    
    # Treatment plan
    handoff.treatment_plan = """
    Cardiology consultation for cardiac catheterization within 24 hours.
    Continue dual antiplatelet therapy and anticoagulation.
    Serial troponins q6h x 3 to trend.
    Monitor on telemetry for arrhythmias.
    Heart failure management with ACE inhibitor and beta-blocker.
    """
    
    # Completed treatments
    handoff.completed_treatments = [
        "Aspirin 324mg loading dose",
        "Atorvastatin 80mg high-intensity statin",
        "Metoprolol 25mg initiated",
        "Heparin anticoagulation per ACS protocol"
    ]
    
    # Pending actions
    handoff.pending_actions = [
        "Cardiology consultation (called, ETA 30 minutes)",
        "Second troponin in 6 hours",
        "Echocardiogram in AM",
        "Lipid panel if not done in past year"
    ]
    
    # Medications
    handoff.medications = [
        {"name": "Aspirin", "dose": "81mg", "frequency": "daily"},
        {"name": "Atorvastatin", "dose": "80mg", "frequency": "nightly"},
        {"name": "Metoprolol", "dose": "25mg", "frequency": "twice daily"},
        {"name": "Lisinopril", "dose": "10mg", "frequency": "daily (continue home med)"},
        {"name": "Metformin", "dose": "1000mg", "frequency": "twice daily (continue home med)"}
    ]
    
    # Allergies
    handoff.allergies = ["NKDA (No Known Drug Allergies)"]
    
    # Follow-up
    handoff.follow_up_needed = [
        "Cardiology follow-up within 1 week of discharge",
        "Primary care follow-up within 1-2 weeks",
        "Cardiac rehabilitation referral",
        "Diabetes management optimization"
    ]
    
    # Social factors
    handoff.social_factors = [
        "Lives with husband, good support system",
        "Retired, no occupational concerns",
        "Insurance: Medicare + supplemental"
    ]
    
    # Specialist notes
    handoff.specialist_notes = "Awaiting cardiology evaluation for catheterization timing. Patient stable for transfer to monitored bed."
    
    # Mark handoff complete
    handoff.mark_complete("Dr. Martinez")
    patient.advance_stage(HandoffStage.TREATMENT_PLAN, "Dr. Martinez")
    patient.target_department = "Cardiology Step-Down Unit"
    
    print("✓ Handoff package completed by Dr. Martinez")
    print(f"✓ Target department: {patient.target_department}")
    
    # === FINAL HANDOFF READY ===
    patient.advance_stage(HandoffStage.READY_TRANSFER, "Dr. Martinez")
    print("\n🎯 PATIENT READY FOR HANDOFF")
    print("-" * 50)
    print(f"✓ Patient {patient.patient_id} ready for transfer")
    print(f"✓ Total ED length of stay: {datetime.now() - patient.arrival_time}")
    print(f"✓ Handoff readiness check: {patient.is_handoff_ready()}")
    
    return coordinator, patient

def generate_handoff_report(coordinator, patient_id):
    """Generate and display the complete handoff report"""
    
    print("\n" + "="*70)
    print("📄 COMPLETE HANDOFF REPORT")
    print("="*70)
    
    # Generate the handoff report
    handoff_report = coordinator.generate_handoff_report(patient_id)
    
    # Display patient information
    patient_info = handoff_report["patient_info"]
    print(f"\n👤 PATIENT INFORMATION")
    print(f"Patient ID: {patient_info['id']}")
    print(f"Age/Gender: {patient_info['age']}yo {patient_info['gender']}")
    print(f"Chief Complaint: {patient_info['chief_complaint']}")
    print(f"Arrival Time: {datetime.fromisoformat(patient_info['arrival_time']).strftime('%m/%d/%Y %H:%M')}")
    print(f"Total Length of Stay: {patient_info['total_los']}")
    print(f"Comorbidities: {', '.join(patient_info['comorbidities'])}")
    
    # Display clinical summary
    clinical = handoff_report["clinical_summary"]
    print(f"\n🩺 CLINICAL SUMMARY")
    print(f"Current Stage: {clinical['current_stage'].replace('_', ' ').title()}")
    print(f"Protocol: {clinical['protocol'].replace('_', ' ').title()}")
    
    # Latest vitals
    if clinical["latest_vitals"]:
        vitals = clinical["latest_vitals"]
        print(f"Latest Vitals: BP {vitals['systolic_bp']}/{vitals['diastolic_bp']}, HR {vitals['heart_rate']}, SpO2 {vitals['oxygen_saturation']}%, Pain {vitals['pain_score']}/10")
    
    # Diagnostics completed
    print(f"\n🔬 COMPLETED DIAGNOSTICS")
    for dx in clinical["diagnostics_completed"]:
        status = "🚨 CRITICAL" if dx["critical"] else "✓"
        print(f"  {status} {dx['test']}: {dx['result']}")
    
    if clinical["pending_diagnostics"]:
        print(f"\n⏳ PENDING DIAGNOSTICS: {', '.join(clinical['pending_diagnostics'])}")
    
    # Handoff package details
    handoff_pkg = handoff_report["handoff_package"]
    print(f"\n📋 HANDOFF PACKAGE")
    print(f"Primary Diagnosis: {handoff_pkg['diagnosis']}")
    if handoff_pkg['differential_diagnoses']:
        print(f"Differential: {', '.join(handoff_pkg['differential_diagnoses'])}")
    
    print(f"\n📝 TREATMENT PLAN:")
    for line in handoff_pkg['treatment_plan'].strip().split('\n'):
        if line.strip():
            print(f"  • {line.strip()}")
    
    print(f"\n✅ COMPLETED TREATMENTS:")
    for treatment in handoff_pkg['completed_treatments']:
        print(f"  • {treatment}")
    
    print(f"\n⏰ PENDING ACTIONS:")
    for action in handoff_pkg['pending_actions']:
        print(f"  • {action}")
    
    print(f"\n💊 MEDICATIONS:")
    for med in handoff_pkg['medications']:
        print(f"  • {med['name']} {med['dose']} {med['frequency']}")
    
    print(f"\n🔄 FOLLOW-UP NEEDED:")
    for followup in handoff_pkg['follow_up_needed']:
        print(f"  • {followup}")
    
    if handoff_pkg['social_factors']:
        print(f"\n👥 SOCIAL FACTORS:")
        for factor in handoff_pkg['social_factors']:
            print(f"  • {factor}")
    
    # Handoff readiness
    print(f"\n🎯 HANDOFF STATUS")
    ready_status = "✅ READY" if handoff_report["ready_for_handoff"] else "❌ NOT READY"
    print(f"Transfer Ready: {ready_status}")
    
    if handoff_report["estimated_completion"]:
        completion_time = datetime.fromisoformat(handoff_report["estimated_completion"])
        print(f"Estimated Completion: {completion_time.strftime('%H:%M')}")
    
    # Alerts
    if handoff_report["alerts"]:
        print(f"\n🚨 ACTIVE ALERTS:")
        for alert in handoff_report["alerts"]:
            print(f"  • {alert['severity'].upper()}: {alert['message']}")
    
    print(f"\n📤 PREPARED BY: {handoff_pkg['prepared_by']} at {datetime.fromisoformat(handoff_pkg['prepared_at']).strftime('%H:%M')}")
    
    return handoff_report

def show_communication_log(coordinator):
    """Display the communication and event log"""
    
    print("\n" + "="*70)
    print("📞 COMMUNICATION & EVENT LOG")
    print("="*70)
    
    # Get the patient to show communication events
    patient = coordinator.patients["ED-2024-0892"]
    
    print("\n📋 Patient Communication Events:")
    for event in patient.communication_events[-10:]:  # Last 10 events
        timestamp = datetime.fromisoformat(event["timestamp"]).strftime("%H:%M:%S")
        print(f"  {timestamp} - {event['event'].replace('_', ' ').title()}: {event.get('test', '')} {event.get('new_status', '')}")
    
    print(f"\n📊 System Communication Summary:")
    comm_summary = coordinator.communication.get_communication_summary(hours_back=1)
    print(f"  Total communications last hour: {comm_summary['total_communications']}")
    
    if coordinator.communication.communication_log:
        print(f"\n📨 Recent System Messages:")
        for msg in coordinator.communication.communication_log[-5:]:  # Last 5 messages
            timestamp = datetime.fromisoformat(msg["timestamp"]).strftime("%H:%M:%S")
            print(f"  {timestamp} - {msg['event_type']}")

def show_dashboard_summary(coordinator):
    """Show key dashboard metrics"""
    
    print("\n" + "="*70)
    print("📊 ED DASHBOARD SUMMARY")
    print("="*70)
    
    dashboard = coordinator.get_comprehensive_dashboard()
    
    # Patient summary
    patient_summary = dashboard["patient_summary"]
    print(f"\n👥 PATIENT CENSUS")
    print(f"Total patients: {patient_summary['total_patients']}")
    print(f"Average LOS: {patient_summary['avg_los']:.1f} hours" if patient_summary['avg_los'] else "Average LOS: N/A")
    print(f"Ready for transfer: {patient_summary['pending_transfers']}")
    
    # Workflow metrics
    workflow = dashboard["workflow_metrics"]
    print(f"\n⚡ WORKFLOW METRICS")
    print(f"Pending diagnostics: {workflow['pending_diagnostics']}")
    print(f"Overdue diagnostics: {workflow['overdue_diagnostics']}")
    if workflow['avg_diagnostic_turnaround']:
        print(f"Avg diagnostic turnaround: {workflow['avg_diagnostic_turnaround']:.0f} minutes")
    print(f"Handoff completion rate: {workflow['handoff_completion_rate']:.0%}")
    
    # Capacity status
    capacity = dashboard["capacity_status"]
    print(f"\n🏥 CAPACITY STATUS")
    print(f"Overall utilization: {capacity['overall_utilization']:.0%}")
    
    if capacity['bottlenecks']:
        print(f"Active bottlenecks:")
        for bottleneck in capacity['bottlenecks']:
            print(f"  • {bottleneck['message']} ({bottleneck['severity']})")
    else:
        print("No capacity bottlenecks detected")
    
    # Alerts
    alerts = dashboard["active_alerts"]
    print(f"\n🚨 ALERT SUMMARY")
    print(f"Total active alerts: {alerts['total_alerts']}")
    print(f"Critical unresolved: {alerts['critical_unresolved']}")
    print(f"Unacknowledged alerts: {alerts['unacknowledged']}")

def main():
    """Run the complete handoff demonstration"""
    
    # Create the scenario
    coordinator, patient = create_realistic_handoff_scenario()
    
    # Generate and display the handoff report
    handoff_report = generate_handoff_report(coordinator, "ED-2024-0892")
    
    # Show communication log
    show_communication_log(coordinator)
    
    # Show dashboard summary
    show_dashboard_summary(coordinator)
    
    print("\n" + "="*70)
    print("✅ HANDOFF DEMONSTRATION COMPLETE")
    print("="*70)
    print("\nThis patient is now ready for seamless handoff to the Cardiology Step-Down Unit")
    print("with complete documentation, clear treatment plan, and all critical information")
    print("properly organized for the receiving team.")

if __name__ == "__main__":
    main()
