
import React, { useMemo, useState } from "react";
import {
  QrCode, MapPin, Clock, Battery, Search, Scan, AlertTriangle, Wrench,
  ShieldAlert, Power, CheckCircle2, XCircle, Timer, RefreshCcw, PlugZap, Lock, Unlock
} from "lucide-react";

/**
 * ED Equipment Tracker (Pro)
 * - Confidence & stale-data warnings (verify-scan CTA)
 * - Maintenance & cleaning lifecycle
 * - Docked/charging & low-battery warnings
 * - Reservation with TTL + conflict handling
 * - Filters (type/status/critical) + sort by ETA, then battery
 * - Simulated QR scan + location update
 * TailwindCSS + lucide-react
 */

type Status = "Available" | "In Use" | "Reserved" | "Missing" | "Unavailable" | "Ready";
type Maintenance = "ok" | "broken";

type Equipment = {
  id: string;
  type: string;
  location: string;
  status: Status;
  battery: number | null;
  lastSeenMin: number;         // minutes since last seen
  confidence: number;          // 0..1
  needsCleaning: boolean;
  maintenance: Maintenance;
  docked: boolean;
  reservation?: { by: string; expiresAt: number }; // epoch ms
};

const LOW_BATT = 30;
const STALE_MIN = 30;
const DEFAULT_ETA = 5;

const ALL_TYPES = ["All", "Ultrasound", "Crash Cart", "Wheelchair", "IV Pump", "Monitor"] as const;
const ALL_STATUS = ["Any", "Available", "In Use", "Reserved", "Missing", "Unavailable", "Ready"] as const;

function etaMinutes(from: string, to: string, confidence: number): number {
  if (!from || !to) return DEFAULT_ETA;
  if (from === to) return 2;
  // one-floor ED heuristic; add penalty for low confidence
  const base = DEFAULT_ETA;
  const penalty = (1 - Math.max(0, Math.min(1, confidence))) * 6;
  return Math.round((base + penalty) * 10) / 10;
}

function statusColor(s: Status) {
  switch (s) {
    case "Available": return "text-green-700 bg-green-100";
    case "In Use": return "text-blue-700 bg-blue-100";
    case "Reserved": return "text-amber-700 bg-amber-100";
    case "Missing": return "text-red-700 bg-red-100";
    case "Unavailable": return "text-gray-700 bg-gray-200";
    case "Ready": return "text-green-700 bg-green-100";
    default: return "text-gray-700 bg-gray-100";
  }
}

function battColor(b: number | null) {
  if (b === null) return "text-gray-400";
  if (b > 50) return "text-green-700";
  if (b > LOW_BATT) return "text-amber-700";
  return "text-red-700";
}

function chip({ text, className }: { text: string; className?: string }) {
  return <span className={`px-2 py-0.5 rounded text-xs font-medium ${className || ""}`}>{text}</span>;
}

function now() { return Date.now(); }

export default function EDEquipmentTrackerPro() {
  const [term, setTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState<typeof ALL_TYPES[number]>("All");
  const [statusFilter, setStatusFilter] = useState<typeof ALL_STATUS[number]>("Any");
  const [criticalOnly, setCriticalOnly] = useState(false);
  const [scannerOpen, setScannerOpen] = useState(false);
  const [scanId, setScanId] = useState<string>("");
  const [scanLoc, setScanLoc] = useState<string>("");

  const [equipment, setEquipment] = useState<Equipment[]>([
    { id: "US_01", type: "Ultrasound", location: "Room 3", status: "In Use", battery: 85, lastSeenMin: 2, confidence: 0.95, needsCleaning: false, maintenance: "ok", docked: false },
    { id: "US_02", type: "Ultrasound", location: "Hallway B", status: "Available", battery: 22, lastSeenMin: 45, confidence: 0.35, needsCleaning: true, maintenance: "ok", docked: false },
    { id: "US_03", type: "Ultrasound", location: "Unknown", status: "Missing", battery: null, lastSeenMin: 120, confidence: 0.15, needsCleaning: false, maintenance: "ok", docked: false },
    { id: "CRASH_01", type: "Crash Cart", location: "Resus 1", status: "Ready", battery: 100, lastSeenMin: 5, confidence: 0.98, needsCleaning: false, maintenance: "ok", docked: true },
    { id: "CRASH_02", type: "Crash Cart", location: "Room 8", status: "In Use", battery: 90, lastSeenMin: 1, confidence: 0.99, needsCleaning: false, maintenance: "ok", docked: false },
    { id: "WC_01", type: "Wheelchair", location: "Main Entrance", status: "Available", battery: null, lastSeenMin: 30, confidence: 0.70, needsCleaning: false, maintenance: "ok", docked: false },
    { id: "IV_01", type: "IV Pump", location: "Room 2", status: "In Use", battery: 45, lastSeenMin: 8, confidence: 0.88, needsCleaning: false, maintenance: "ok", docked: false },
    { id: "MON_01", type: "Monitor", location: "Hallway A", status: "Available", battery: 75, lastSeenMin: 12, confidence: 0.85, needsCleaning: false, maintenance: "ok", docked: true },
  ]);

  const LOCATIONS = ["ED", "Room 1", "Room 2", "Room 3", "Room 4", "Room 5", "Room 6", "Room 7", "Room 8", "Resus 1", "Resus 2", "Hallway A", "Hallway B", "Main Entrance", "Triage", "Storage"];

  function update(id: string, patch: Partial<Equipment>) {
    setEquipment(prev => prev.map(e => (e.id === id ? { ...e, ...patch } : e)));
  }

  function reserve(id: string, by = "ED-OPS", ttlMin = 10) {
    setEquipment(prev => prev.map(e => {
      if (e.id !== id) return e;
      if (e.status === "In Use" || e.status === "Reserved" || e.maintenance === "broken") return e; // reject conflicts
      return { ...e, status: "Reserved", reservation: { by, expiresAt: now() + ttlMin * 60_000 } };
    }));
  }
  function release(id: string) { update(id, { status: "Available", reservation: undefined }); }

  function verifyScan(id: string, newLoc: string) {
    update(id, { location: newLoc, lastSeenMin: 0, confidence: 0.99, status: (prevOf(id)?.status === "Missing" ? "Available" : prevOf(id)?.status) || "Available" });
  }
  function prevOf(id: string) { return equipment.find(e => e.id === id); }

  function reportBroken(id: string) { update(id, { maintenance: "broken", status: "Unavailable" }); }
  function resolveMaintenance(id: string) { update(id, { maintenance: "ok", status: "Available" }); }
  function markCleaned(id: string) { update(id, { needsCleaning: false }); }
  function toggleDocked(id: string) { update(id, { docked: !(prevOf(id)?.docked ?? false) }); }

  // Expire reservations
  const _ = useMemo(() => {
    const nowMs = now();
    const changed: string[] = [];
    equipment.forEach(e => {
      if (e.reservation && e.reservation.expiresAt <= nowMs) {
        changed.push(e.id);
      }
    });
    if (changed.length) {
      setEquipment(prev => prev.map(e => e.reservation && e.reservation.expiresAt <= nowMs ? { ...e, reservation: undefined, status: "Available" } : e));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [equipment.map(e => e.reservation?.expiresAt).join(",")]);

  const filtered = useMemo(() => {
    return equipment
      .filter(e => {
        const txt = `${e.id} ${e.type} ${e.location}`.toLowerCase();
        const matchesTerm = term.trim() === "" || txt.includes(term.toLowerCase());
        const matchesType = typeFilter === "All" || e.type === typeFilter;
        const matchesStatus = statusFilter === "Any" || e.status === statusFilter;
        const critical = (e.confidence < 0.5) || (e.lastSeenMin > STALE_MIN) || (typeof e.battery === "number" && e.battery <= LOW_BATT) || e.maintenance === "broken" || e.needsCleaning;
        const matchesCritical = !criticalOnly || critical;
        return matchesTerm && matchesType && matchesStatus && matchesCritical;
      })
      .map(e => ({
        ...e,
        eta: etaMinutes(e.location, "ED", e.confidence),
      }))
      .sort((a, b) => (a.eta - b.eta) || ((b.battery ?? -1) - (a.battery ?? -1)));
  }, [equipment, term, typeFilter, statusFilter, criticalOnly]);

  function simulateScan() {
    const ids = equipment.map(e => e.id);
    const rnd = ids[Math.floor(Math.random() * ids.length)];
    setScanId(rnd);
  }

  return (
    <div className="max-w-7xl mx-auto p-6 bg-gray-50 min-h-screen">
      <div className="bg-white rounded-2xl shadow">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <QrCode className="w-8 h-8 text-blue-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">ED Equipment Tracker</h1>
              <p className="text-sm text-gray-600">Locate, reserve, and maintain shared devices</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setScannerOpen(true)}
              className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              <Scan className="w-4 h-4" />
              Scan QR
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="p-6 bg-gray-50 border-b border-gray-200">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div className="relative col-span-2">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                className="pl-10 pr-3 py-2 w-full border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Search by ID, type, or location..."
                value={term}
                onChange={e => setTerm(e.target.value)}
              />
            </div>
            <select
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              value={typeFilter}
              onChange={e => setTypeFilter(e.target.value as any)}
            >
              {ALL_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <div className="flex items-center gap-2">
              <select
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value as any)}
              >
                {ALL_STATUS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <label className="flex items-center gap-2 text-sm text-gray-700 select-none">
                <input type="checkbox" checked={criticalOnly} onChange={e => setCriticalOnly(e.target.checked)} />
                Critical only
              </label>
            </div>
          </div>
        </div>

        {/* Grid */}
        <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(e => {
            const isLowBatt = typeof e.battery === "number" && e.battery <= LOW_BATT;
            const isStale = e.lastSeenMin > STALE_MIN || e.confidence < 0.5;
            const canReserve = e.status === "Available" && e.maintenance === "ok";
            return (
              <div key={e.id} className="border border-gray-200 rounded-xl p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-lg text-gray-900">{e.id}</h3>
                    <p className="text-sm text-gray-600">{e.type}</p>
                  </div>
                  {chip({ text: e.status, className: statusColor(e.status) })}
                </div>

                <div className="mt-3 space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <MapPin className="w-4 h-4 text-gray-400" />
                    <span>{e.location}</span>
                    {isStale && <AlertTriangle className="w-4 h-4 text-amber-500" title="Location likely stale — verify scan" />}
                    {e.docked && <PlugZap className="w-4 h-4 text-green-600" title="Docked/charging" />}
                  </div>

                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <Clock className="w-4 h-4 text-gray-400" />
                    <span>Last seen: {e.lastSeenMin} min</span>
                    <Timer className="w-4 h-4 text-gray-400 ml-3" />
                    <span>ETA to ED: {e.eta} min</span>
                  </div>

                  {e.battery !== null && (
                    <div className="flex items-center gap-2 text-sm">
                      <Battery className={`w-4 h-4 ${battColor(e.battery)}`} />
                      <span className={`${battColor(e.battery)} font-medium`}>
                        {e.battery}% {isLowBatt && "(low)"}
                      </span>
                    </div>
                  )}

                  <div className="flex flex-wrap gap-2 text-xs">
                    {e.needsCleaning && chip({ text: "Needs cleaning", className: "text-amber-700 bg-amber-100" })}
                    {e.maintenance === "broken" && chip({ text: "Broken", className: "text-red-700 bg-red-100" })}
                    {isStale && chip({ text: `Confidence ${Math.round(e.confidence*100)}%`, className: "text-amber-700 bg-amber-100" })}
                    {e.reservation && chip({ text: `Reserved until ${new Date(e.reservation.expiresAt).toLocaleTimeString()}`, className: "text-amber-700 bg-amber-100" })}
                  </div>
                </div>

                {/* Actions */}
                <div className="mt-3 pt-3 border-t border-gray-100 grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setScannerOpen(true) || setScanId(e.id)}
                    className="flex items-center justify-center gap-2 px-3 py-2 border rounded-lg hover:bg-gray-50"
                    title="Verify location via scan"
                  >
                    <QrCode className="w-4 h-4" /> Verify scan
                  </button>

                  {canReserve ? (
                    <button
                      onClick={() => reserve(e.id)}
                      className="flex items-center justify-center gap-2 px-3 py-2 border rounded-lg hover:bg-gray-50"
                      title="Reserve for 10 minutes"
                    >
                      <Lock className="w-4 h-4" /> Reserve
                    </button>
                  ) : e.status === "Reserved" ? (
                    <button
                      onClick={() => release(e.id)}
                      className="flex items-center justify-center gap-2 px-3 py-2 border rounded-lg hover:bg-gray-50"
                      title="Release reservation"
                    >
                      <Unlock className="w-4 h-4" /> Release
                    </button>
                  ) : (
                    <button
                      disabled
                      className="flex items-center justify-center gap-2 px-3 py-2 border rounded-lg opacity-50 cursor-not-allowed"
                      title="Not reservable now"
                    >
                      <Lock className="w-4 h-4" /> Reserve
                    </button>
                  )}

                  {e.needsCleaning ? (
                    <button
                      onClick={() => markCleaned(e.id)}
                      className="flex items-center justify-center gap-2 px-3 py-2 border rounded-lg hover:bg-gray-50"
                    >
                      <CheckCircle2 className="w-4 h-4 text-green-600" /> Mark cleaned
                    </button>
                  ) : (
                    <button disabled className="flex items-center justify-center gap-2 px-3 py-2 border rounded-lg opacity-50 cursor-not-allowed">
                      <CheckCircle2 className="w-4 h-4" /> Mark cleaned
                    </button>
                  )}

                  {e.maintenance === "ok" ? (
                    <button
                      onClick={() => reportBroken(e.id)}
                      className="flex items-center justify-center gap-2 px-3 py-2 border rounded-lg hover:bg-gray-50"
                    >
                      <ShieldAlert className="w-4 h-4 text-red-600" /> Report broken
                    </button>
                  ) : (
                    <button
                      onClick={() => resolveMaintenance(e.id)}
                      className="flex items-center justify-center gap-2 px-3 py-2 border rounded-lg hover:bg-gray-50"
                    >
                      <Wrench className="w-4 h-4" /> Resolve maintenance
                    </button>
                  )}

                  <button
                    onClick={() => toggleDocked(e.id)}
                    className="flex items-center justify-center gap-2 px-3 py-2 border rounded-lg hover:bg-gray-50 col-span-2"
                  >
                    <Power className="w-4 h-4" /> {e.docked ? "Undock" : "Dock/charge"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Scanner Modal */}
        {scannerOpen && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md">
              <h3 className="text-lg font-semibold mb-4">QR Code Scanner</h3>
              <div className="p-8 border-2 border-dashed rounded-lg text-center text-gray-600 mb-4">
                <QrCode className="w-16 h-16 mx-auto mb-2 text-gray-400" />
                <p>Position QR code in camera view</p>
                <button className="text-blue-600 text-sm underline mt-2" onClick={simulateScan}>
                  Simulate scan
                </button>
              </div>
              <div className="grid gap-3 mb-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Scanned ID</label>
                  <input
                    className="w-full border rounded-lg px-3 py-2"
                    placeholder="US_01"
                    value={scanId}
                    onChange={e => setScanId(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">New location</label>
                  <select className="w-full border rounded-lg px-3 py-2" value={scanLoc} onChange={e => setScanLoc(e.target.value)}>
                    <option value="">Select location...</option>
                    {LOCATIONS.map(l => <option key={l} value={l}>{l}</option>)}
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => {
                    if (scanId && scanLoc) {
                      verifyScan(scanId, scanLoc);
                      setScannerOpen(false);
                      setScanId(""); setScanLoc("");
                    }
                  }}
                  className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                  disabled={!scanId || !scanLoc}
                >
                  Update location
                </button>
                <button className="flex-1 bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300" onClick={() => { setScannerOpen(false); setScanId(""); setScanLoc(""); }}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer / Legend */}
      <div className="text-xs text-gray-500 mt-4 flex items-center gap-4">
        <div className="flex items-center gap-1"><AlertTriangle className="w-3 h-3 text-amber-500" /> Verify scan if confidence &lt; 50% or lastSeen &gt; {STALE_MIN} min</div>
        <div className="flex items-center gap-1"><Battery className="w-3 h-3 text-red-700" /> Low battery &le; {LOW_BATT}%</div>
        <div className="flex items-center gap-1"><PlugZap className="w-3 h-3 text-green-600" /> Docked/charging</div>
        <div className="flex items-center gap-1"><Lock className="w-3 h-3" /> 10‑min reservation TTL</div>
        <button className="ml-auto inline-flex items-center gap-1 text-blue-600 hover:text-blue-700"><RefreshCcw className="w-3 h-3" /> Refresh</button>
      </div>
    </div>
  );
}
