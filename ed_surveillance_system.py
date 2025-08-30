# === ED Surveillance and Early Warning System ===
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import json

@dataclass
class SurveillanceAlert:
    """Structure for surveillance alerts"""
    alert_type: str
    severity: str  # "info", "warning", "critical"
    message: str
    confidence: float
    data_points: Dict[str, Any]
    recommended_actions: List[str]
    timestamp: datetime

class EpiSurveillanceML:
    """ML model for epidemiological surveillance and early warning"""
    
    def __init__(self, lookback_days: int = 14):
        self.lookback_days = lookback_days
        self.baseline_patterns = {}
        self.seasonal_adjustments = {
            "influenza": {"peak_months": [12, 1, 2, 3], "factor": 2.5},
            "rsv": {"peak_months": [11, 12, 1, 2], "factor": 2.0},
            "norovirus": {"peak_months": [11, 12, 1, 2, 3, 4], "factor": 1.8},
            "respiratory_other": {"peak_months": [10, 11, 12, 1, 2, 3], "factor": 1.5}
        }
    
    def analyze_patient_patterns(self, recent_patients: List[Dict[str, Any]]) -> List[SurveillanceAlert]:
        """Analyze recent patient patterns for surveillance alerts"""
        
        if not recent_patients:
            return []
        
        alerts = []
        current_time = datetime.now(timezone.utc)
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(recent_patients)
        
        # 1. Respiratory syndrome surveillance
        resp_alert = self._detect_respiratory_surge(df, current_time)
        if resp_alert:
            alerts.append(resp_alert)
        
        # 2. GI syndrome surveillance  
        gi_alert = self._detect_gi_surge(df, current_time)
        if gi_alert:
            alerts.append(gi_alert)
        
        # 3. Acuity pattern changes
        acuity_alert = self._detect_acuity_changes(df, current_time)
        if acuity_alert:
            alerts.append(acuity_alert)
        
        # 4. Volume surge prediction
        volume_alert = self._predict_volume_surge(df, current_time)
        if volume_alert:
            alerts.append(volume_alert)
        
        # 5. Age demographic shifts
        demo_alert = self._detect_demographic_shifts(df, current_time)
        if demo_alert:
            alerts.append(demo_alert)
        
        return alerts
    
    def _detect_respiratory_surge(self, df: pd.DataFrame, current_time: datetime) -> Optional[SurveillanceAlert]:
        """Detect respiratory illness surges (flu, RSV, COVID)"""
        
        # Identify respiratory cases by chief complaint and symptoms
        respiratory_keywords = [
            "dyspnoe", "dyspnea", "atemprobleme", "husten", "cough", 
            "fieber", "fever", "schüttelfrost", "chest pain", "brustschmerz"
        ]
        
        resp_cases = df[df.get("chief_complaint", "").str.lower().str.contains("|".join(respiratory_keywords), na=False)]
        
        if len(resp_cases) == 0:
            return None
        
        # Calculate respiratory case rate
        total_cases = len(df)
        resp_rate = len(resp_cases) / total_cases
        
        # Seasonal adjustment
        current_month = current_time.month
        seasonal_factor = 1.0
        
        for syndrome, params in self.seasonal_adjustments.items():
            if current_month in params["peak_months"]:
                seasonal_factor = max(seasonal_factor, params["factor"])
        
        expected_rate = 0.15 / seasonal_factor  # Baseline 15% respiratory complaints
        
        # Alert thresholds
        if resp_rate > expected_rate * 2.0:
            severity = "critical"
            message = f"Respiratory surge detected: {resp_rate:.1%} of cases (expected {expected_rate:.1%})"
            actions = [
                "Activate respiratory triage protocol",
                "Ensure isolation capacity available", 
                "Consider rapid antigen testing",
                "Alert infection control team"
            ]
        elif resp_rate > expected_rate * 1.5:
            severity = "warning"
            message = f"Increased respiratory cases: {resp_rate:.1%} of cases (expected {expected_rate:.1%})"
            actions = [
                "Monitor respiratory case trends",
                "Review isolation bed availability",
                "Consider enhanced PPE protocols"
            ]
        else:
            return None
        
        return SurveillanceAlert(
            alert_type="respiratory_surge",
            severity=severity,
            message=message,
            confidence=min(0.95, resp_rate / expected_rate * 0.3),
            data_points={
                "respiratory_rate": resp_rate,
                "expected_rate": expected_rate,
                "seasonal_factor": seasonal_factor,
                "case_count": len(resp_cases),
                "total_count": total_cases
            },
            recommended_actions=actions,
            timestamp=current_time
        )
    
    def _detect_gi_surge(self, df: pd.DataFrame, current_time: datetime) -> Optional[SurveillanceAlert]:
        """Detect GI illness surges (norovirus, food poisoning)"""
        
        gi_keywords = [
            "übelkeit", "nausea", "erbrechen", "vomiting", "durchfall", "diarrhea",
            "bauchschmerz", "abdominal", "gastroenteritis"
        ]
        
        gi_cases = df[df.get("chief_complaint", "").str.lower().str.contains("|".join(gi_keywords), na=False)]
        
        if len(gi_cases) == 0:
            return None
        
        gi_rate = len(gi_cases) / len(df)
        expected_rate = 0.08  # Baseline 8% GI complaints
        
        # Seasonal adjustment for norovirus
        if current_time.month in self.seasonal_adjustments["norovirus"]["peak_months"]:
            expected_rate /= 1.5
        
        if gi_rate > expected_rate * 2.5:
            return SurveillanceAlert(
                alert_type="gi_surge",
                severity="warning",
                message=f"GI illness surge detected: {gi_rate:.1%} of cases (expected {expected_rate:.1%})",
                confidence=gi_rate / expected_rate * 0.25,
                data_points={"gi_rate": gi_rate, "expected_rate": expected_rate, "cases": len(gi_cases)},
                recommended_actions=[
                    "Consider norovirus outbreak investigation",
                    "Enhance hand hygiene protocols",
                    "Review isolation procedures",
                    "Alert public health if cluster identified"
                ],
                timestamp=current_time
            )
        
        return None
    
    def _detect_acuity_changes(self, df: pd.DataFrame, current_time: datetime) -> Optional[SurveillanceAlert]:
        """Detect changes in patient acuity patterns"""
        
        if "triage" not in df.columns:
            return None
        
        # Convert triage to numeric (1=Red, 2=Orange, 3=Yellow, 4=Green, 5=Blue)
        triage_mapping = {"red": 1, "orange": 2, "yellow": 3, "green": 4, "blue": 5, "rot": 1, "orange": 2, "gelb": 3, "grün": 4, "blau": 5}
        
        numeric_triage = df["triage"].str.lower().map(triage_mapping)
        
        if numeric_triage.isna().all():
            return None
        
        high_acuity_rate = (numeric_triage <= 2).sum() / len(numeric_triage.dropna())
        expected_high_acuity = 0.20  # Expected 20% red/orange
        
        if high_acuity_rate > expected_high_acuity * 1.8:
            return SurveillanceAlert(
                alert_type="acuity_increase",
                severity="warning",
                message=f"High acuity surge: {high_acuity_rate:.1%} red/orange cases (expected {expected_high_acuity:.1%})",
                confidence=0.8,
                data_points={
                    "high_acuity_rate": high_acuity_rate,
                    "expected_rate": expected_high_acuity
                },
                recommended_actions=[
                    "Consider activating additional senior staff",
                    "Review ICU bed availability",
                    "Alert department head",
                    "Prepare for potential capacity issues"
                ],
                timestamp=current_time
            )
        
        return None
    
    def _predict_volume_surge(self, df: pd.DataFrame, current_time: datetime) -> Optional[SurveillanceAlert]:
        """Predict incoming volume surge based on recent patterns"""
        
        # Analyze arrival patterns from recent hours
        if "arrival_time" not in df.columns:
            return None
        
        # Convert arrival times and calculate arrivals per hour
        try:
            arrival_times = pd.to_datetime(df["arrival_time"])
            recent_hours = arrival_times[arrival_times > (current_time - timedelta(hours=4))]
            
            if len(recent_hours) == 0:
                return None
            
            # Calculate current arrival rate (patients/hour)
            hours_analyzed = min(4, (current_time - recent_hours.min()).total_seconds() / 3600)
            current_rate = len(recent_hours) / hours_analyzed
            
            # Expected rates by time of day
            hour = current_time.hour
            if 8 <= hour <= 12:  # Morning surge
                expected_rate = 12
            elif 16 <= hour <= 22:  # Evening surge  
                expected_rate = 15
            elif 22 <= hour or hour <= 6:  # Night
                expected_rate = 6
            else:
                expected_rate = 9
            
            if current_rate > expected_rate * 1.6:
                return SurveillanceAlert(
                    alert_type="volume_surge",
                    severity="warning",
                    message=f"Volume surge detected: {current_rate:.1f} patients/hour (expected {expected_rate})",
                    confidence=0.7,
                    data_points={
                        "current_rate": current_rate,
                        "expected_rate": expected_rate,
                        "hours_analyzed": hours_analyzed
                    },
                    recommended_actions=[
                        "Consider opening additional triage stations",
                        "Alert nursing supervisor",
                        "Review discharge readiness list",
                        "Prepare for extended wait times"
                    ],
                    timestamp=current_time
                )
        
        except Exception:
            pass
        
        return None
    
    def _detect_demographic_shifts(self, df: pd.DataFrame, current_time: datetime) -> Optional[SurveillanceAlert]:
        """Detect unusual demographic patterns (age shifts suggesting specific illnesses)"""
        
        if "age" not in df.columns:
            return None
        
        ages = pd.to_numeric(df["age"], errors="coerce").dropna()
        
        if len(ages) < 10:  # Need minimum sample size
            return None
        
        # Detect high pediatric volume (RSV, other pediatric illness)
        pediatric_rate = (ages < 18).sum() / len(ages)
        expected_pediatric = 0.15  # Expected 15% pediatric
        
        if pediatric_rate > expected_pediatric * 2.5:
            return SurveillanceAlert(
                alert_type="pediatric_surge",
                severity="info",
                message=f"Increased pediatric cases: {pediatric_rate:.1%} (expected {expected_pediatric:.1%})",
                confidence=0.6,
                data_points={"pediatric_rate": pediatric_rate, "expected_rate": expected_pediatric},
                recommended_actions=[
                    "Consider RSV/pediatric illness surveillance",
                    "Review pediatric bed availability",
                    "Alert pediatric staff if available"
                ],
                timestamp=current_time
            )
        
        return None

def generate_mock_patients(hours_back: int = 6, base_rate: int = 8) -> List[Dict[str, Any]]:
    """Generate realistic mock patients for testing surveillance"""
    
    patients = []
    current_time = datetime.now(timezone.utc)
    
    # Generate patients over recent hours
    for hour_offset in range(hours_back):
        hour_start = current_time - timedelta(hours=hour_offset+1)
        
        # Vary arrival rate by time
        if hour_start.hour in [9, 10, 11, 18, 19, 20]:
            hourly_rate = base_rate * 1.5  # Surge hours
        elif hour_start.hour in [2, 3, 4, 5]:
            hourly_rate = base_rate * 0.3  # Night hours
        else:
            hourly_rate = base_rate
        
        # Generate patients for this hour
        for _ in range(int(np.random.poisson(hourly_rate))):
            arrival_time = hour_start + timedelta(minutes=np.random.randint(0, 60))
            
            # Chief complaints with seasonal variation
            complaints = ["brustschmerz", "bauchschmerz", "kopfschmerzen", "schwindel", "sturz"]
            
            # Add seasonal respiratory complaints
            if current_time.month in [11, 12, 1, 2, 3]:
                complaints.extend(["dyspnoe", "husten", "fieber"] * 3)  # Increase probability
            
            # Add GI complaints with cluster probability
            if np.random.random() < 0.1:  # 10% chance of GI cluster
                complaints.extend(["übelkeit", "erbrechen", "durchfall"] * 4)
            
            patients.append({
                "patient_id": f"mock_{len(patients)}",
                "arrival_time": arrival_time.isoformat(),
                "chief_complaint": np.random.choice(complaints),
                "age": max(1, int(np.random.normal(45, 20))),
                "triage": np.random.choice(["green", "yellow", "orange", "red"], p=[0.4, 0.35, 0.2, 0.05])
            })
    
    return patients

# Integration with existing gate engine
def surveillance_enhanced_gate_engine(fd: Dict[str, Any], CONFIG: Dict[str, Any]) -> Dict[str, Any]:
    """Gate engine enhanced with surveillance early warning"""
    
    # Run standard gate engine
    result = gate_engine(fd, CONFIG)
    
    # Add surveillance if enabled
    if CONFIG.get("USE_SURVEILLANCE", False):
        try:
            # Get recent patient data (in production, from EMR)
            recent_patients = generate_mock_patients(hours_back=4)  # Mock for demo
            
            # Run surveillance analysis
            surveillance = EpiSurveillanceML()
            alerts = surveillance.analyze_patient_patterns(recent_patients)
            
            # Add alerts to gate result
            result["surveillance_alerts"] = []
            for alert in alerts:
                result["surveillance_alerts"].append({
                    "type": alert.alert_type,
                    "severity": alert.severity,
                    "message": alert.message,
                    "confidence": alert.confidence,
                    "actions": alert.recommended_actions
                })
                
                # Convert high-priority alerts to gates
                if alert.severity == "critical":
                    result["gates"].append(f"SURVEILLANCE_{alert.alert_type.upper()}")
                    result["priority"] = max(result.get("priority", 0), 4)
            
            # Log surveillance results
            _append_event({
                "type": "surveillance_analysis",
                "patient_id": fd.get("patient_id", "unknown"),
                "alerts_count": len(alerts),
                "alerts": [{"type": a.alert_type, "severity": a.severity} for a in alerts]
            })
            
        except Exception as e:
            # Surveillance failure shouldn't break gate engine
            result["surveillance_error"] = str(e)
    
    return result

# Surveillance UI for clinical oversight
def add_surveillance_ui():
    """Add surveillance dashboard to existing UI"""
    
    if not CONFIG.get("RUN_UI"):
        return
        
    try:
        import ipywidgets as W
        
        # Surveillance toggle
        surveillance_toggle = W.Checkbox(
            description="Enable Surveillance Alerts",
            value=CONFIG.get("USE_SURVEILLANCE", False)
        )
        
        # Real-time surveillance check
        check_btn = W.Button(description="Check Current Patterns", button_style="info")
        surveillance_out = W.Output()
        
        def check_surveillance(_):
            with surveillance_out:
                surveillance_out.clear_output()
                print("Analyzing recent patient patterns...")
                
                # Generate test data
                patients = generate_mock_patients(hours_back=6)
                surveillance = EpiSurveillanceML()
                alerts = surveillance.analyze_patient_patterns(patients)
                
                if not alerts:
                    print("✓ No surveillance alerts detected")
                    print(f"Analyzed {len(patients)} patients from last 6 hours")
                else:
                    print(f"⚠ {len(alerts)} surveillance alerts detected:")
                    for alert in alerts:
                        severity_icon = {"info": "ℹ", "warning": "⚠", "critical": "🚨"}
                        icon = severity_icon.get(alert.severity, "?")
                        print(f"\n{icon} {alert.severity.upper()}: {alert.message}")
                        print(f"   Confidence: {alert.confidence:.1%}")
                        if alert.recommended_actions:
                            print("   Recommended actions:")
                            for action in alert.recommended_actions[:3]:
                                print(f"   • {action}")
        
        check_btn.on_click(check_surveillance)
        
        # Historical trends (placeholder)
        trends_btn = W.Button(description="View Trends", button_style="success")
        trends_out = W.Output()
        
        def show_trends(_):
            with trends_out:
                trends_out.clear_output()
                print("Historical surveillance trends:")
                print("• Respiratory cases: Baseline (no surge detected)")
                print("• GI cases: Slightly elevated (monitor)")
                print("• Volume: Normal for time of day")
                print("• Acuity: Within expected range")
                print("\n(Real implementation would show actual trend charts)")
        
        trends_btn.on_click(show_trends)
        
        display(W.VBox([
            W.HTML("<b>ED Surveillance Dashboard</b>"),
            W.HTML("<i>Early warning system for epidemiological patterns and operational changes</i>"),
            surveillance_toggle,
            W.HBox([check_btn, trends_btn]),
            surveillance_out,
            trends_out
        ]))
        
    except Exception as e:
        print("Surveillance UI unavailable:", e)

print("ED Surveillance System loaded")
print("- Use surveillance_enhanced_gate_engine() for surveillance + gates")
print("- Set CONFIG['USE_SURVEILLANCE'] = True to enable")
print("- Call add_surveillance_ui() for clinical dashboard")