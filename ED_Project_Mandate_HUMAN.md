# Projekt-Mandat — ED Coordination Assistant (Urban) · v2025-08-13
**Ziel:** Automatisierung/semi-Automatisierung administrativer & logistischer Workflows in der Notaufnahme — **ohne** medizinische Entscheidungen.

**Setting:** Städtische ED, hohes Aufkommen · Akteure: EMS, Triage-Pflege, ED-Ärzt:innen, Diagnostik, Station/ICU · KIS: Orbis (simuliert), HL7/JSON-Bridge.

**Scope (Stufen):**
1) EMS → **Pre-Alert** (Triageflag, Vitalwerte, Allergien, Voraufenthalte)  
2) **Capacity Check** (Betten/ICU; Stale-Erkennung)  
3) **ED-Ankunft** (Re-Triage, vorbereitete Orders *für Bestätigung*)  
4) **Intra-ED Koordination** (Status-Tracking, Result-Benachr., Reminders)  
5) **Specialist Handoff** (Vorschlag Ziel-Fachbereich, Transferkoordination)

**Guardrails:** Keine Diagnose/Therapie; **Human-in-the-loop** für alle Orders/Anmeldungen; vollständiges Audit-Log; **keine Echtdaten** im PoC.

**Nicht-Ziele:** Keine AI-Diagnose, keine autonome Therapie, kein Live-KIS-Einsatz.

**KPIs/Proxies:** Minutenersparnis/Patient (Admin), weniger Unterbrechungen/Schicht, TtT kritisch, zuverlässige Benachrichtigung.

**Standards:** Sprache: DE; Zeitzone: Europe/Berlin; Einheiten: Minuten; Datenschutz: synthetic-only.
