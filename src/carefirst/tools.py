# Mock KIS tools (replace with real adapters later)

def lab_status(patient_id: str):
    return {"patient_id": patient_id, "labs": {"CRP": "noch ausstehend"}}

def transport_eta(order_id: str):
    return {"order_id": order_id, "eta_min": 15}

def admission_status(patient_id: str):
    return {"patient_id": patient_id, "station": "Innere Medizin", "status": "Wartend"}

TOOLS = {
    "lab_status": lab_status,
    "transport_eta": transport_eta,
    "admission_status": admission_status,
}
