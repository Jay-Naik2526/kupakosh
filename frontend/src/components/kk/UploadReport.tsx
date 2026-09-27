"use client";
import { useEffect, useState } from "react";
import { API, get } from "@/lib/api";
import { useApp } from "@/lib/state";
import { t } from "@/lib/i18n";

const KINDS: [string, string][] = [
  ["DDR_PDF", "Daily drilling report"], ["WCR_PDF", "Well completion report"], ["EOWR_PDF", "End-of-well report"],
  ["WELL_HISTORY", "Well history / summary"], ["INCIDENT_REPORT", "Incident report"], ["OTHER", "Other (search only, no events)"],
];
const KINDS_HI: Record<string, string> = {
  DDR_PDF: "दैनिक वेधन रिपोर्ट (DDR)", WCR_PDF: "कूप समापन रिपोर्ट (WCR)", EOWR_PDF: "अंत-कूप रिपोर्ट (EOWR)",
  WELL_HISTORY: "कूप इतिहास / सारांश", INCIDENT_REPORT: "घटना रिपोर्ट", OTHER: "अन्य (केवल खोज हेतु, कोई घटना नहीं)",
};

/** Upload a report -> background job (text, events, episodes, affected wiki pages back to review). */
export function UploadReport() {
  const { user, wellId, country, lang } = useApp();
  const [file, setFile] = useState<File | null>(null);
  const [kind, setKind] = useState("DDR_PDF");
  const [well, setWell] = useState("");
  const [cc, setCc] = useState(country ?? "");
  const [job, setJob] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (wellId && !well) get(`/api/wells/${wellId}`).then((w) => setWell(w.name)).catch(() => {}); }, [wellId]); // eslint-disable-line
  useEffect(() => {
    if (!job || job.status === "done" || job.status === "failed") return;
    const h = setTimeout(() => get(`/api/jobs/${job.id}`).then(setJob).catch(() => {}), 1000);
    return () => clearTimeout(h);
  }, [job]);

  const send = async () => {
    if (!file) return;
    setErr(null); setBusy(true); setJob(null);
    const fd = new FormData();
    fd.append("file", file); fd.append("kind", kind);
    if (well.trim()) fd.append("well", well.trim());
    if (cc.trim()) fd.append("country", cc.trim());
    if (user) fd.append("uploader", user.name);
    try {
      const r = await fetch(`${API}/api/ingest`, { method: "POST", body: fd });
      if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
      setJob(await r.json());
    } catch (e: any) { setErr(e.message); }
    setBusy(false);
  };

  return (
    <div className="space-y-3 small">
      <p>{lang === "hi"
        ? "एक रिपोर्ट जोड़ें (PDF, TXT, HTML या XML)। Kupakosh इसे संग्रहीत करता है, उद्धरण-योग्य वाक्यों में विभाजित करता है, नामित कूप हेतु घटनाएँ निकालता है, उस कूप के घटना-क्रम पुनः जोड़ता है, और परिवर्तित ज्ञानकोश पृष्ठों को पुनः समीक्षा हेतु भेजता है।"
        : "Add a report (PDF, TXT, HTML or XML). Kupakosh stores it, splits it into citable sentences, extracts events for the named well, re-links that well's episodes and sends the changed wiki pages back to review."}</p>
      <div className="grid gap-2" style={{ gridTemplateColumns: "9rem 1fr" }}>
        <label className="label" htmlFor="upf">{lang === "hi" ? "फ़ाइल" : "File"}</label>
        <input id="upf" type="file" accept=".pdf,.txt,.html,.htm,.xml" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <label className="label" htmlFor="upk">{lang === "hi" ? "रिपोर्ट प्रकार" : "Report type"}</label>
        <select id="upk" className="input" value={kind} onChange={(e) => setKind(e.target.value)}>{KINDS.map(([k, l]) => <option key={k} value={k}>{lang === "hi" ? KINDS_HI[k] ?? l : l}</option>)}</select>
        <label className="label" htmlFor="upw">{t("well", lang)}</label>
        <input id="upw" className="input" value={well} onChange={(e) => setWell(e.target.value)} placeholder={lang === "hi" ? "मौजूदा कूप नाम, या नया नाम" : "existing well name, or a new one"} />
        <label className="label" htmlFor="upc">{t("countryLabel", lang)}</label>
        <input id="upc" className="input" value={cc} onChange={(e) => setCc(e.target.value)} placeholder={lang === "hi" ? "जैसे भारत (नए कूप हेतु प्रयुक्त)" : "e.g. India (used for a new well)"} />
      </div>
      <p className="label">{lang === "hi" ? "नए कूप का नाम बिना स्थान के बनाया जाता है। स्कैन किए गए PDF संग्रहीत हैं परंतु पढ़े नहीं गए: इस निर्माण में OCR स्थापित नहीं है।" : "A new well name is created without a location. Scanned PDFs are stored but not read: OCR is not installed in this build."}</p>
      <button className="btn btn-primary" disabled={!file || busy} onClick={send}>{busy ? (lang === "hi" ? "अपलोड हो रहा है…" : "Uploading…") : (lang === "hi" ? "अपलोड करें व संसाधित करें" : "Upload and process")}</button>
      {err && <div className="border rounded-kk p-2" style={{ borderColor: "var(--hazard)" }}>✕ {err}</div>}
      {job && (
        <div className="border rounded-kk p-3" style={{
          borderColor: `color-mix(in srgb, ${job.status === "failed" ? "var(--hazard)" : job.status === "done" ? "var(--ok)" : "var(--caution)"} 45%, var(--border))`,
          background: `color-mix(in srgb, ${job.status === "failed" ? "var(--hazard)" : job.status === "done" ? "var(--ok)" : "var(--caution)"} 8%, var(--card))`,
        }}>
          <div className="font-semibold">Job {job.id} · <span className="mono" style={{ color: job.status === "failed" ? "var(--hazard)" : job.status === "done" ? "#166534" : "var(--caution-ink)" }}>{job.status}</span>{job.status === "failed" ? " ✕" : job.status === "done" ? " ✓" : " …"}</div>
          <ol className="list-decimal pl-5 mt-1 space-y-0.5">{job.steps.map((s: any, i: number) => <li key={i} className="break-words">{s.msg}</li>)}</ol>
          {job.error && <p style={{ color: "var(--hazard)" }}>{job.error}</p>}
          {job.result?.document_id && <p className="mt-1">{lang === "hi" ? "इस रूप में संग्रहीत" : "Stored as"} <span className="mono">doc:{job.result.document_id}</span>{job.result.duplicate_of ? (lang === "hi" ? " (पहले से लोड — कुछ नहीं जोड़ा गया)" : " (already loaded — nothing added)") : ""}.</p>}
        </div>
      )}
    </div>
  );
}
