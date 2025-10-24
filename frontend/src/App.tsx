
import React, { useEffect, useMemo, useState } from "react";

// --- Types (kept in sync with backend) ---
export type Robot = { name: string; status: "IDLE" | "EXECUTING"; node: string };
export type Order = { name: string; source: string; target: string; status: "NEW" | "IN_PROGRESS" | "DONE" | "FAILED" };
export type Graph = { nodes: string[]; edges: { from: string; to: string; weight: number }[] };

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// --- Data hooks ---
function usePoll<T>(fn: () => Promise<T>, deps: any[] = [], intervalMs = 1000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;
    const tick = async () => {
      try {
        const val = await fn();
        if (!cancelled) setData(val);
      } catch (e: any) {
        if (!cancelled) setError(e);
      } finally {
        if (!cancelled) timer = window.setTimeout(tick, intervalMs);
      }
    };
    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, deps);
  return { data, error } as const;
}

// --- Simple layout: place nodes in a circle ---
function circularLayout(nodes: string[], width: number, height: number) {
  const r = Math.min(width, height) * 0.35;
  const cx = width / 2;
  const cy = height / 2;
  const step = (2 * Math.PI) / Math.max(nodes.length, 1);
  const pos = new Map<string, { x: number; y: number }>();
  nodes.forEach((n, i) => {
    pos.set(n, { x: cx + r * Math.cos(i * step - Math.PI / 2), y: cy + r * Math.sin(i * step - Math.PI / 2) });
  });
  return pos;
}

// --- UI Components ---
function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl shadow p-4 bg-white/80 border border-gray-200">
      <div className="text-sm font-semibold text-gray-700 mb-2">{title}</div>
      {children}
    </div>
  );
}

function Legend() {
  return (
    <div className="flex gap-4 text-xs text-gray-600">
      <div className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-full bg-gray-800" /> Node</div>
      <div className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-full bg-green-600" /> Robot (IDLE)</div>
      <div className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-full bg-orange-500" /> Robot (EXECUTING)</div>
      <div className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded bg-gray-400" style={{width: 16, height: 3}} /> Edge</div>
    </div>
  );
}

export default function App() {
  const { data: graphRes, error: gErr } = usePoll<Graph>(() => api<Graph>("/getGraph"), [], 3000);
  const { data: robotsRes, error: rErr } = usePoll<{ robots: Robot[] }>(() => api<{ robots: Robot[] }>("/getRobots"), [], 1000);
  const { data: ordersRes, error: oErr } = usePoll<{ orders: Order[] }>(() => api<{ orders: Order[] }>("/getOrders"), [], 1000);

  const nodes = graphRes?.nodes ?? [];
  const edges = graphRes?.edges ?? [];
  const robots = robotsRes?.robots ?? [];
  const orders = ordersRes?.orders ?? [];

  const [width, height] = [720, 420];
  const positions = useMemo(() => circularLayout(nodes, width, height), [nodes, width, height]);

  // Add Order form state
  const [form, setForm] = useState<{ name: string; source: string; target: string }>({ name: "", source: "", target: "" });
  const [submitting, setSubmitting] = useState(false);
  const [submitErr, setSubmitErr] = useState<string | null>(null);

  const submitOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitErr(null);
    if (!form.name || !form.source || !form.target) {
      setSubmitErr("Please fill all fields");
      return;
    }
    try {
      setSubmitting(true);
      await api("/addOrder", { method: "POST", body: JSON.stringify(form) });
      setForm({ name: "", source: "", target: "" });
    } catch (err: any) {
      setSubmitErr(err?.message || "Failed to add order");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 text-gray-900">
      <div className="max-w-6xl mx-auto px-4 py-6">
        <header className="flex items-baseline justify-between mb-4">
          <h1 className="text-2xl font-bold tracking-tight">AGV Scheduler UI (stub)</h1>
          <Legend />
        </header>

        {/* Main grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Map */}
          <Panel title="Map">
            <div className="overflow-auto">
                {/* here goes the map rendering logic */}
            </div>
            {(gErr || rErr || oErr) && (
              <div className="mt-2 text-sm text-red-600">{gErr?.message || rErr?.message || oErr?.message}</div>
            )}
          </Panel>

          {/* Right column: Orders & Robots */}
          <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
            <Panel title="Add Order">
              <form onSubmit={submitOrder} className="grid grid-cols-2 gap-3">
                <label className="col-span-2 text-xs text-gray-600">Name
                  <input className="mt-1 w-full border rounded-lg px-3 py-2" value={form.name} onChange={(e) => setForm(v => ({ ...v, name: e.target.value }))} placeholder="O-1234" />
                </label>
                <label className="text-xs text-gray-600">Source
                  <select className="mt-1 w-full border rounded-lg px-3 py-2" value={form.source} onChange={(e) => setForm(v => ({ ...v, source: e.target.value }))}>
                    <option value="">-- select --</option>
                    {nodes.map(n => <option key={n} value={n}>{n}</option>)}
                  </select>
                </label>
                <label className="text-xs text-gray-600">Target
                  <select className="mt-1 w-full border rounded-lg px-3 py-2" value={form.target} onChange={(e) => setForm(v => ({ ...v, target: e.target.value }))}>
                    <option value="">-- select --</option>
                    {nodes.map(n => <option key={n} value={n}>{n}</option>)}
                  </select>
                </label>
                <div className="col-span-2 flex items-center gap-3">
                  <button disabled={submitting} className="px-4 py-2 rounded-xl bg-black text-white disabled:opacity-50">Add</button>
                  {submitErr && <span className="text-xs text-red-600">{submitErr}</span>}
                </div>
              </form>
            </Panel>

            <Panel title={`Orders (${orders.length})`}>
              <div className="max-h-64 overflow-auto divide-y">
                {orders.map(o => (
                  <div key={o.name} className="py-2 flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium">{o.name}</div>
                      <div className="text-xs text-gray-600">{o.source} → {o.target}</div>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full ${o.status === "NEW" ? "bg-yellow-100 text-yellow-700" : o.status === "IN_PROGRESS" ? "bg-blue-100 text-blue-700" : o.status === "DONE" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>{o.status}</span>
                  </div>
                ))}
                {orders.length === 0 && <div className="text-sm text-gray-500 py-4">No orders</div>}
              </div>
            </Panel>

            <Panel title={`Robots (${robots.length})`}>
              <div className="max-h-64 overflow-auto divide-y">
                {robots.map(r => (
                  <div key={r.name} className="py-2 flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium">{r.name}</div>
                      <div className="text-xs text-gray-600">Node: {r.node}</div>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full ${r.status === "IDLE" ? "bg-green-100 text-green-700" : "bg-orange-100 text-orange-700"}`}>{r.status}</span>
                  </div>
                ))}
                {robots.length === 0 && <div className="text-sm text-gray-500 py-4">No robots</div>}
              </div>
            </Panel>

            <Panel title="Dev Tools">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <button
                  onClick={() => api("/tick", { method: "POST" }).catch(() => {})}
                  className="px-3 py-1 rounded-lg border bg-white hover:bg-gray-50"
                  title="Advance the simulation on the server (if implemented)"
                >Tick</button>
                <span className="text-xs text-gray-500">API: {API_BASE}</span>
              </div>
            </Panel>
          </div>
        </div>

        <footer className="mt-6 text-xs text-gray-500">
          This is a minimal stub UI. Add here as part of the exercise.
        </footer>
      </div>
    </div>
  );
}
