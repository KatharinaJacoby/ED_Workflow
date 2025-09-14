# === GATE ENGINE TESTING - OPERATIONAL SCENARIOS ===
# Test the gate engine with realistic ED scenarios that demonstrate protected constraints

if CONFIG.get("RUN_PIPELINE"):
    print("🧪 Testing Gate Engine with Operational Scenarios")
    print("="*60)
    
    # Test current time scenarios (demonstrates protected timing constraints)
    from datetime import datetime
    
    # Scenario times
    morning_time = datetime(2025, 8, 23, 9, 30)   # 9:30 AM - good time
    evening_time = datetime(2025, 8, 23, 17, 0)   # 5:00 PM - bed managers gone  
    night_time = datetime(2025, 8, 23, 23, 30)    # 11:30 PM - night shift resistance
    weekend_time = datetime(2025, 8, 23, 14, 0)   # Saturday 2:00 PM - weekend
    
    test_scenarios = [
        {
            "name": "PROTECTED CONSTRAINT: Abdominal Pain - Mandatory Hold",
            "description": "Tests that mandatory 24hr hold cannot be overridden",
            "features": {
                'Tag': 2, 't_min': 90, 'Triage': 3, 'Leitsymptom': 'abdominal_pain',
                'HF': 85, 'MAP': 90, 'ICU_Kap': 6, 'hat_Labor': True,
                'Labor_ausstehend': False, 'CT_ausstehend': False,
                'naechste_Aktion': 'observation', 'age': 42
            },
            "calculators": {'heart': 1, 'qsofa': 0, 'troponin_flag': False},
            "time": morning_time,
            "expected": "Should be BLOCKED due to mandatory abdominal pain hold"
        },
        
        {
            "name": "PROTECTED CONSTRAINT: Evening Transfer (5pm)",
            "description": "Tests bed manager cutoff constraint",
            "features": {
                'Tag': 2, 't_min': 120, 'Triage': 3, 'Leitsymptom': 'pneumonia',
                'HF': 95, 'MAP': 80, 'ICU_Kap': 4, 'hat_Labor': True,
                'Labor_ausstehend': False, 'CT_ausstehend': False,
                'naechste_Aktion': 'transfer', 'age': 67
            },
            "calculators": {'heart': 2, 'qsofa': 1, 'troponin_flag': False},
            "time": evening_time,
            "expected": "Should show operational timing constraints (bed managers off duty)"
        },
        
        {
            "name": "PROTECTED CONSTRAINT: Night Shift Resistance",
            "description": "Tests night shift transfer patterns",
            "features": {
                'Tag': 3, 't_min': 180, 'Triage': 4, 'Leitsymptom': 'stable_condition',
                'HF': 78, 'MAP': 85, 'ICU_Kap': 5, 'hat_Labor': True,
                'Labor_ausstehend': False, 'CT_ausstehend': False,
                'naechste_Aktion': 'transfer', 'age': 55
            },
            "calculators": {'heart': 1, 'qsofa': 0, 'troponin_flag': False},
            "time": night_time,
            "expected": "Should show night shift resistance penalty"
        },
        
        {
            "name": "HIGH ACUITY: Chest Pain with High HEART Score",
            "description": "Tests integration with clinical calculators",
            "features": {
                'Tag': 1, 't_min': 200, 'Triage': 2, 'Leitsymptom': 'chest_pain',
                'HF': 125, 'MAP': 65, 'ICU_Kap': 2, 'hat_Labor': True,
                'Labor_ausstehend': True, 'CT_ausstehend': False,
                'naechste_Aktion': 'cardiology', 'age': 68
            },
            "calculators": {'heart': 7, 'qsofa': 1, 'troponin_flag': True},
            "time": morning_time,
            "expected": "Should be high priority but blocked by incomplete cardiac workup"
        },
        
        {
            "name": "SEPSIS ALERT: High qSOFA + Suspected Infection",
            "description": "Tests sepsis protocol enforcement",
            "features": {
                'Tag': 1, 't_min': 75, 'Triage': 1, 'Leitsymptom': 'fever_hypotension',
                'HF': 130, 'MAP': 55, 'ICU_Kap': 1, 'hat_Labor': True,
                'Labor_ausstehend': True, 'CT_ausstehend': False,
                'naechste_Aktion': 'icu_evaluation', 'age': 72
            },
            "calculators": {'heart': 3, 'qsofa': 3, 'troponin_flag': False},
            "time": morning_time,
            "expected": "Should be highest priority with sepsis bundle requirements"
        },
        
        {
            "name": "BOARDING PATIENT: >5 Hours in ED",
            "description": "Tests boarding threshold constraints",
            "features": {
                'Tag': 3, 't_min': 350, 'Triage': 4, 'Leitsymptom': 'awaiting_placement',
                'HF': 80, 'MAP': 85, 'ICU_Kap': 5, 'hat_Labor': True,
                'Labor_ausstehend': False, 'CT_ausstehend': False,
                'naechste_Aktion': 'awaiting_bed', 'age': 78
            },
            "calculators": {'heart': 1, 'qsofa': 0, 'troponin_flag': False},
            "time": morning_time,
            "expected": "Should get priority boost due to boarding threshold"
        },
        
        {
            "name": "READY FOR DISCHARGE: All Gates Open",
            "description": "Tests optimal scenario with no constraints",
            "features": {
                'Tag': 4, 't_min': 180, 'Triage': 4, 'Leitsymptom': 'minor_complaint',
                'HF': 72, 'MAP': 88, 'ICU_Kap': 7, 'hat_Labor': True,
                'Labor_ausstehend': False, 'CT_ausstehend': False,
                'naechste_Aktion': 'discharge', 'age': 28
            },
            "calculators": {'heart': 0, 'qsofa': 0, 'troponin_flag': False},
            "time": morning_time,
            "expected": "Should show all gates open, low priority, ready for disposition"
        }
    ]
    
    # Run test scenarios
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\\n🧪 Test {i}: {scenario['name']}")
        print(f"📝 {scenario['description']}")
        print(f"⏰ Time: {scenario['time'].strftime('%A %I:%M %p')}")
        print("-" * 50)
        
        # Run gate engine assessment
        try:
            result = gate_engine.compute_overall_readiness(
                scenario['features'], 
                scenario['calculators'], 
                {'age': scenario['features']['age']},
                scenario['time']
            )
            
            # Display results
            print(f"🎯 Priority: {result['priority']}/10")
            print(f"📊 Readiness: {result['overall_readiness']:.2f}")
            print(f"🚪 Gates: {result['gates']}")
            print(f"⚡ Next Action: {result['next_action']}")
            
            # Show critical constraints
            critical_gates = result.get('critical_gates', [])
            if critical_gates:
                print(f"🔴 BLOCKED BY: {', '.join(critical_gates)}")
            
            # Show ETA if applicable
            if result.get('eta_minutes'):
                hours = result['eta_minutes'] // 60
                mins = result['eta_minutes'] % 60
                eta_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
                print(f"⏱️ ETA to Resolution: {eta_str}")
            
            # Show detailed gate breakdown for critical cases
            if result['priority'] >= 8 or critical_gates:
                print("\\n🔍 Detailed Gate Analysis:")
                for category, gate in result['gate_details'].items():
                    if gate.status != "open":
                        status_emoji = {"pending": "🟡", "blocked": "🔴"}.get(gate.status, "❓")
                        print(f"  {status_emoji} {category}: {', '.join(gate.blockers[:2])}")
            
            print(f"✅ Expected: {scenario['expected']}")
            
            # Validate key constraints are working
            validation_notes = []
            
            # Check abdominal pain constraint
            if 'abdominal' in scenario['features']['Leitsymptom']:
                if any('mandatory' in str(gate.blockers).lower() for gate in result['gate_details'].values()):
                    validation_notes.append("✅ Mandatory abdominal pain hold enforced")
                else:
                    validation_notes.append("❌ Abdominal pain constraint failed")
            
            # Check time-based constraints
            hour = scenario['time'].hour
            if hour >= 17:  # After 5pm
                timing_gate = result['gate_details'].get('operational_timing')
                if timing_gate and 'bed managers' in str(timing_gate.blockers).lower():
                    validation_notes.append("✅ Evening bed manager constraint enforced")
            
            # Check sepsis protocol
            if scenario['calculators'].get('qsofa', 0) >= 2:
                safety_gate = result['gate_details'].get('clinical_safety')
                medical_gate = result['gate_details'].get('medical_completion')
                if (safety_gate and 'sepsis' in str(safety_gate.blockers).lower()) or \
                   (medical_gate and 'sepsis' in str(medical_gate.blockers).lower()):
                    validation_notes.append("✅ Sepsis protocol enforced")
            
            if validation_notes:
                print("\\n🔒 Protected Constraint Validation:")
                for note in validation_notes:
                    print(f"  {note}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary of protected constraints
    print("\\n" + "="*60)
    print("🔒 PROTECTED CONSTRAINTS SUMMARY")
    print("="*60)
    print("✅ These operational rules CANNOT be overridden by MLP:")
    print("  • Abdominal pain = mandatory 24hr hold")
    print("  • Bed managers off duty after 4pm")
    print("  • Night shift transfer resistance (10pm-6am)")
    print("  • High acuity patients >2hr need urgent review")
    print("  • Sepsis protocols must be completed")
    print("  • ICU capacity thresholds")
    print("  • Minimum observation times")
    print("\\n💡 MLP can only REFINE priority, never override safety constraints")
    print("🎯 Gate engine = primary decision, MLP = secondary calibration")
    
else:
    print("⚠️ Gate engine testing skipped - set CONFIG['RUN_PIPELINE']=True")