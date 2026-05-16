"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, CheckCircle2, Copy, Download, ExternalLink, Loader2, Mail, Search, Send, Sparkles, Target, Users } from "lucide-react";
import { MarketingAgentInput, MarketingAgentOutput, ProspectAnalysis } from "@/lib/marketing-agent";

const defaultInput: MarketingAgentInput = {
  objective: "Get more qualified local businesses to apply for a free Summit partner build this quarter.",
  market: "restaurants, salons, contractors, retail shops, animal care businesses, clinics, and appointment-based local services",
  offer: "custom AI-powered website, chatbot or booking assistant, local SEO, analytics, and full code ownership at no service cost",
  location: "United States local business markets, with priority on businesses that already have reviews but weak websites",
  audience: "business owners who need more calls, bookings, quote requests, or online orders but do not want to spend thousands on an agency",
  constraints: "Do not make fake guarantees. Be clear that clients still pay for domain and hosting. Keep outreach personal and respectful.",
};

const starterLeads = `Luxe Hair Studio, https://example.com, owner@example.com, salon with online booking opportunity
Main Street Roofing, https://example.com, no clear quote request flow
Bright Paws Grooming, Instagram only, strong reviews but no website listed`;

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        await navigator.clipboard.writeText(value);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1200);
      }}
      className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-gray-200 bg-white text-gray-500 hover:text-[#1B3A6B]"
      aria-label="Copy"
    >
      {copied ? <CheckCircle2 size={16} className="text-green-600" /> : <Copy size={16} />}
    </button>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-bold uppercase tracking-[0.14em] text-[#1B3A6B]">{label}</span>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        rows={3}
        className="w-full resize-none rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm leading-relaxed text-[#0D1E3D] shadow-sm focus:border-[#1B3A6B] focus:ring-4 focus:ring-[#1B3A6B]/10"
      />
    </label>
  );
}

function statusClass(status: ProspectAnalysis["status"]) {
  if (status === "approved") return "bg-green-50 text-green-700";
  if (status === "contacted") return "bg-blue-50 text-blue-700";
  if (status === "not_fit") return "bg-gray-100 text-gray-500";
  return "bg-[#1B3A6B]/8 text-[#1B3A6B]";
}

function fitClass(fit: ProspectAnalysis["fit"]) {
  if (fit === "high") return "bg-green-50 text-green-700";
  if (fit === "medium") return "bg-[#F47B20]/10 text-[#8a3e09]";
  return "bg-gray-100 text-gray-500";
}

function csvEscape(value: unknown) {
  return `"${String(value ?? "").replace(/"/g, '""')}"`;
}

export default function MarketingAgent() {
  const [input, setInput] = useState(defaultInput);
  const [rawLeads, setRawLeads] = useState(starterLeads);
  const [plan, setPlan] = useState<MarketingAgentOutput | null>(null);
  const [prospects, setProspects] = useState<ProspectAnalysis[]>(() => {
    if (typeof window === "undefined") return [];
    const saved = window.localStorage.getItem("summit_marketing_prospects");
    if (!saved) return [];
    try {
      return JSON.parse(saved) as ProspectAnalysis[];
    } catch {
      return [];
    }
  });
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [loadingProspects, setLoadingProspects] = useState(false);
  const [sendingIndex, setSendingIndex] = useState<number | null>(null);
  const [gmailConnected, setGmailConnected] = useState(false);
  const [error, setError] = useState("");

  const planText = useMemo(() => (plan ? JSON.stringify(plan, null, 2) : ""), [plan]);
  const approvedCount = prospects.filter((prospect) => prospect.status === "approved").length;
  const contactedCount = prospects.filter((prospect) => prospect.status === "contacted").length;

  useEffect(() => {
    if (prospects.length) localStorage.setItem("summit_marketing_prospects", JSON.stringify(prospects));
  }, [prospects]);

  useEffect(() => {
    fetch("/api/gmail/status")
      .then((res) => res.json())
      .then((data) => setGmailConnected(Boolean(data.connected)))
      .catch(() => setGmailConnected(false));
  }, []);

  const setField = (key: keyof MarketingAgentInput, value: string) => setInput((prev) => ({ ...prev, [key]: value }));

  const runPlan = async () => {
    setLoadingPlan(true);
    setError("");
    try {
      const res = await fetch("/api/marketing-agent", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "Plan failed.");
      setPlan(data.plan);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoadingPlan(false);
    }
  };

  const analyzeProspects = async () => {
    setLoadingProspects(true);
    setError("");
    try {
      const res = await fetch("/api/marketing-agent/prospects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...input, rawLeads }) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "Prospect analysis failed.");
      setProspects(data.prospects || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoadingProspects(false);
    }
  };

  const updateStatus = (index: number, status: ProspectAnalysis["status"]) => {
    setProspects((prev) => prev.map((prospect, i) => (i === index ? { ...prospect, status } : prospect)));
  };

  const exportProspects = () => {
    const rows = [
      ["Business", "Website", "Email", "Score", "Fit", "Status", "Observation", "Opportunity", "Subject", "Email Draft", "Next Action"],
      ...prospects.map((p) => [p.businessName, p.website, p.email, p.score, p.fit, p.status, p.specificObservation, p.opportunity, p.subject, p.emailDraft, p.nextAction]),
    ];
    const blob = new Blob([rows.map((row) => row.map(csvEscape).join(",")).join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "summit-marketing-prospects.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  const sendWithGmail = async (prospect: ProspectAnalysis, index: number) => {
    setSendingIndex(index);
    setError("");
    try {
      const res = await fetch("/api/gmail/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          to: prospect.email,
          subject: prospect.subject,
          body: prospect.emailDraft,
          approved: prospect.status === "approved",
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "Gmail send failed.");
      updateStatus(index, "contacted");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gmail send failed.");
    } finally {
      setSendingIndex(null);
    }
  };

  return (
    <main className="min-h-screen bg-[#f8fafc]">
      <section className="border-b border-gray-200 bg-white px-6 py-12">
        <div className="mx-auto max-w-7xl">
          <span className="section-label">Standalone Summit Growth Agent</span>
          <h1 className="max-w-4xl text-4xl font-black leading-tight tracking-tight text-[#0D1E3D] md:text-6xl">
            Semi-autonomous AI marketer for finding and converting local business prospects.
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-relaxed text-gray-500">
            Generate strategy, score leads, inspect public website text, write outreach, approve prospects, track status, and export CSV.
          </p>
        </div>
      </section>

      <section className="px-6 py-10">
        <div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[430px_1fr]">
          <aside className="h-fit rounded-lg border border-gray-200 bg-white p-6 shadow-sm lg:sticky lg:top-8">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-[#F47B20] text-white">
                <Sparkles size={20} />
              </div>
              <div>
                <h2 className="text-lg font-black text-[#0D1E3D]">Campaign Brief</h2>
                <p className="text-sm text-gray-500">Tune the agent before it works.</p>
              </div>
            </div>
            <div className="space-y-4">
              <Field label="Goal" value={input.objective} onChange={(v) => setField("objective", v)} />
              <Field label="Market" value={input.market} onChange={(v) => setField("market", v)} />
              <Field label="Offer" value={input.offer} onChange={(v) => setField("offer", v)} />
              <Field label="Location" value={input.location} onChange={(v) => setField("location", v)} />
              <Field label="Audience" value={input.audience} onChange={(v) => setField("audience", v)} />
              <Field label="Rules" value={input.constraints} onChange={(v) => setField("constraints", v)} />
            </div>
            {error && <p className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
            <button
              type="button"
              onClick={runPlan}
              disabled={loadingPlan}
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-[#1B3A6B] px-5 py-3.5 text-sm font-bold text-white shadow-md shadow-[#1B3A6B]/15 hover:bg-[#F47B20] disabled:opacity-60"
            >
              {loadingPlan ? <Loader2 size={17} className="animate-spin" /> : <ArrowRight size={17} />}
              {loadingPlan ? "Building plan..." : "Run Strategy Agent"}
            </button>
          </aside>

          <div className="space-y-8">
            <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="mt-1 flex h-10 w-10 items-center justify-center rounded-lg bg-[#1B3A6B] text-white"><Users size={19} /></div>
                  <div>
                    <h2 className="text-2xl font-black tracking-tight text-[#0D1E3D]">Semi-Autonomous Prospecting</h2>
                    <p className="mt-1 text-sm leading-relaxed text-gray-500">Paste leads, let the agent score/write, then approve before contact.</p>
                  </div>
                </div>
                {prospects.length > 0 && (
                  <button type="button" onClick={exportProspects} className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-bold text-[#1B3A6B]">
                    <Download size={15} /> Export CSV
                  </button>
                )}
                <a href="/api/gmail/auth" className="inline-flex items-center gap-2 rounded-lg bg-[#1B3A6B] px-3 py-2 text-sm font-bold text-white hover:bg-[#F47B20]">
                  <Mail size={15} /> {gmailConnected ? "Reconnect Gmail" : "Connect Gmail"}
                </a>
              </div>

              <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
                <div>
                  <span className="mb-2 block text-xs font-bold uppercase tracking-[0.14em] text-[#1B3A6B]">Lead List</span>
                  <textarea value={rawLeads} onChange={(event) => setRawLeads(event.target.value)} rows={9} className="w-full resize-none rounded-lg border border-gray-200 bg-[#f8fafc] px-4 py-3 text-sm leading-relaxed text-[#0D1E3D]" />
                  <button type="button" onClick={analyzeProspects} disabled={loadingProspects} className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-[#F47B20] px-5 py-3 text-sm font-bold text-white hover:bg-[#1B3A6B] disabled:opacity-60">
                    {loadingProspects ? <Loader2 size={17} className="animate-spin" /> : <Search size={17} />}
                    {loadingProspects ? "Scoring leads..." : "Analyze Leads"}
                  </button>
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
                  {[[prospects.length, "analyzed"], [approvedCount, "approved"], [contactedCount, "contacted"]].map(([value, label]) => (
                    <div key={label} className="rounded-lg border border-gray-200 bg-[#f8fafc] p-4 text-center">
                      <p className="text-3xl font-black text-[#1B3A6B]">{value}</p>
                      <p className="mt-1 text-xs font-bold uppercase tracking-[0.12em] text-gray-400">{label}</p>
                    </div>
                  ))}
                  <div className="rounded-lg border border-[#1B3A6B]/10 bg-[#1B3A6B]/5 p-4 sm:col-span-3">
                    <h3 className="text-sm font-black text-[#0D1E3D]">
                      Gmail status: {gmailConnected ? "connected" : "not connected"}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-gray-600">
                      The agent still requires approval before sending. Mark a prospect approved, then use Send with Gmail.
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-6 space-y-4">
                {prospects.map((prospect, index) => (
                  <div key={`${prospect.businessName}-${index}`} className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-xl font-black text-[#0D1E3D]">{prospect.businessName}</h3>
                          <span className={`rounded-full px-2.5 py-1 text-xs font-bold uppercase ${fitClass(prospect.fit)}`}>{prospect.fit} fit</span>
                          <span className={`rounded-full px-2.5 py-1 text-xs font-bold uppercase ${statusClass(prospect.status)}`}>{prospect.status.replace("_", " ")}</span>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-3 text-sm text-gray-500">
                          <span className="font-bold text-[#1B3A6B]">Score {prospect.score}</span>
                          {prospect.website && <a href={prospect.website} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-[#1B3A6B]">Website <ExternalLink size={13} /></a>}
                          {prospect.email && <span>{prospect.email}</span>}
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button type="button" onClick={() => updateStatus(index, "approved")} className="rounded-lg bg-green-600 px-3 py-2 text-xs font-bold text-white">Approve</button>
                        <button type="button" onClick={() => updateStatus(index, "contacted")} className="rounded-lg bg-[#1B3A6B] px-3 py-2 text-xs font-bold text-white">Mark Contacted</button>
                        <button type="button" onClick={() => updateStatus(index, "not_fit")} className="rounded-lg border border-gray-200 px-3 py-2 text-xs font-bold text-gray-500">Not Fit</button>
                      </div>
                    </div>
                    <div className="mt-5 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
                      <div className="space-y-3 text-sm leading-relaxed text-gray-600">
                        <p><strong className="text-[#0D1E3D]">Observation:</strong> {prospect.specificObservation}</p>
                        <p><strong className="text-[#0D1E3D]">Opportunity:</strong> {prospect.opportunity}</p>
                        <p><strong className="text-[#0D1E3D]">Next:</strong> {prospect.nextAction}</p>
                      </div>
                      <div className="rounded-lg border border-gray-200 bg-white p-4">
                        <div className="mb-3 flex items-center justify-between gap-3">
                          <div>
                            <p className="text-xs font-black uppercase tracking-[0.12em] text-[#1B3A6B]">Email Draft</p>
                            <p className="mt-1 text-sm font-bold text-[#0D1E3D]">{prospect.subject}</p>
                          </div>
                          <div className="flex gap-2">
                            <CopyButton value={`Subject: ${prospect.subject}\n\n${prospect.emailDraft}`} />
                            <button
                              type="button"
                              onClick={() => sendWithGmail(prospect, index)}
                              disabled={!gmailConnected || !prospect.email || prospect.status !== "approved" || sendingIndex === index}
                              className="inline-flex h-9 items-center justify-center gap-2 rounded-lg bg-green-600 px-3 text-xs font-bold text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:bg-gray-300"
                            >
                              {sendingIndex === index ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
                              Gmail
                            </button>
                            <a href={`mailto:${prospect.email || ""}?subject=${encodeURIComponent(prospect.subject)}&body=${encodeURIComponent(prospect.emailDraft)}`} onClick={() => updateStatus(index, "contacted")} className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-[#1B3A6B] text-white hover:bg-[#F47B20]" aria-label="Open email draft"><Send size={15} /></a>
                          </div>
                        </div>
                        <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-lg bg-[#f8fafc] p-4 font-sans text-sm leading-relaxed text-gray-600">{prospect.emailDraft}</pre>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {plan && (
              <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
                <div className="mb-4 flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div className="mt-1 flex h-10 w-10 items-center justify-center rounded-lg bg-[#1B3A6B] text-white"><Target size={19} /></div>
                    <div>
                      <h2 className="text-2xl font-black tracking-tight text-[#0D1E3D]">{plan.positioning.headline}</h2>
                      <p className="mt-1 text-sm leading-relaxed text-gray-500">{plan.positioning.angle}</p>
                    </div>
                  </div>
                  <CopyButton value={planText} />
                </div>
                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="rounded-lg bg-[#f8fafc] p-5">
                    <h3 className="mb-3 flex items-center gap-2 text-sm font-black uppercase tracking-[0.12em] text-[#1B3A6B]"><Mail size={15} /> Cold Email</h3>
                    <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-gray-600">{plan.outreach.coldEmail}</pre>
                  </div>
                  <div className="rounded-lg bg-[#f8fafc] p-5">
                    <h3 className="mb-3 text-sm font-black uppercase tracking-[0.12em] text-[#1B3A6B]">Weekly Execution</h3>
                    <ul className="space-y-2 text-sm leading-relaxed text-gray-600">
                      {plan.weeklyExecution.map((day) => <li key={day.day}><strong>{day.day}:</strong> {day.priority}</li>)}
                    </ul>
                  </div>
                </div>
              </section>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
