// ---------------------------------------------------------------------------
// THE NEGOTIATOR — API LAYER
// ---------------------------------------------------------------------------
// This is the ONE file that talks to the backend. Every page/component in
// this app calls a function from here — never `fetch` directly from a page.
// That means: when the backend team hands you real endpoints, you plug them
// in HERE and every screen updates automatically.
//
// HOW TO WIRE IN THE REAL BACKEND
// 1. Set NEXT_PUBLIC_API_BASE_URL in .env.local to the backend's base URL,
//    e.g. NEXT_PUBLIC_API_BASE_URL=https://api.thenegotiator.app
// 2. Set NEXT_PUBLIC_USE_MOCKS=false in .env.local.
// 3. Each function below has a `// BACKEND CALL` block already written for
//    the endpoint shape described in the project brief — uncomment/adjust
//    the fetch and delete the corresponding mock call beneath it.
//
// Until then, USE_MOCKS=true (the default) makes the whole app runnable and
// demo-able with realistic fake data and network-like delays, so frontend
// work never blocks on the backend being ready.
// ---------------------------------------------------------------------------

import type {
  JobSpec,
  NegotiationProgress,
  QuoteReport,
  CallTranscript,
  CompanyCall,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS !== "false";

function delay<T>(value: T, ms = 900): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// 1. UPLOAD  —  POST /upload  (multipart/form-data, field name: "file")
//    Returns: { jobId: string }
// ---------------------------------------------------------------------------
export async function uploadJobDocument(file: File): Promise<{ jobId: string }> {
  if (!USE_MOCKS) {
    // BACKEND CALL
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: form });
    if (!res.ok) throw new Error("Upload failed");
    return res.json();
  }
  return delay({ jobId: "job_" + Math.random().toString(36).slice(2, 8) }, 800);
}

// ---------------------------------------------------------------------------
// 2. GET JOB SPEC  —  GET /job/:jobId
//    Returns the extracted JobSpec. Poll this on the Processing page until
//    status moves from "extracting" -> "ready_for_review".
// ---------------------------------------------------------------------------
export async function getJobSpec(jobId: string): Promise<JobSpec> {
  if (!USE_MOCKS) {
    // BACKEND CALL
    return http<JobSpec>(`/job/${jobId}`);
  }
  return delay(mockJobSpec(jobId), 700);
}

// ---------------------------------------------------------------------------
// 3. UPDATE JOB SPEC  —  PUT /job/:jobId
//    Sent when the user edits a field on the Review page before confirming.
// ---------------------------------------------------------------------------
export async function updateJobSpec(jobId: string, patch: Partial<JobSpec>): Promise<JobSpec> {
  if (!USE_MOCKS) {
    // BACKEND CALL
    return http<JobSpec>(`/job/${jobId}`, { method: "PUT", body: JSON.stringify(patch) });
  }
  return delay({ ...mockJobSpec(jobId), ...patch }, 400);
}

// ---------------------------------------------------------------------------
// 4. CONFIRM & START NEGOTIATION  —  POST /job/:jobId/confirm
//    Fired by the "Start Negotiation" button on the Review page.
// ---------------------------------------------------------------------------
export async function confirmJobSpec(jobId: string): Promise<{ started: boolean }> {
  if (!USE_MOCKS) {
    // BACKEND CALL
    return http<{ started: boolean }>(`/job/${jobId}/confirm`, { method: "POST" });
  }
  return delay({ started: true }, 500);
}

// ---------------------------------------------------------------------------
// 5. NEGOTIATION PROGRESS  —  GET /job/:jobId/negotiation
//    Poll this every ~2s on the Negotiation Progress page (or swap for a
//    WebSocket/Socket.io subscription — see lib/useNegotiationSocket.ts stub
//    at the bottom of this file for where that would plug in instead).
// ---------------------------------------------------------------------------
export async function getNegotiationProgress(jobId: string): Promise<NegotiationProgress> {
  if (!USE_MOCKS) {
    // BACKEND CALL
    return http<NegotiationProgress>(`/job/${jobId}/negotiation`);
  }
  return delay(mockProgress(jobId), 300);
}

// ---------------------------------------------------------------------------
// 6. FINAL REPORT / QUOTES  —  GET /job/:jobId/report  (brief calls this
//    GET /quotes — adjust the path to whatever the backend team ships)
// ---------------------------------------------------------------------------
export async function getQuoteReport(jobId: string): Promise<QuoteReport> {
  if (!USE_MOCKS) {
    // BACKEND CALL
    return http<QuoteReport>(`/job/${jobId}/report`);
  }
  return delay(mockReport(jobId), 700);
}

// ---------------------------------------------------------------------------
// 7. COMPANY DETAIL  —  GET /job/:jobId/company/:companyId
// ---------------------------------------------------------------------------
export async function getCompanyDetail(jobId: string, companyId: string): Promise<CompanyCall> {
  if (!USE_MOCKS) {
    // BACKEND CALL
    return http<CompanyCall>(`/job/${jobId}/company/${companyId}`);
  }
  const report = mockReport(jobId);
  const found = report.companies.find((c) => c.companyId === companyId);
  return delay(found ?? report.companies[0], 400);
}

// ---------------------------------------------------------------------------
// 8. CALL TRANSCRIPT (optional page)  —  GET /job/:jobId/company/:companyId/transcript
// ---------------------------------------------------------------------------
export async function getCallTranscript(jobId: string, companyId: string): Promise<CallTranscript> {
  if (!USE_MOCKS) {
    // BACKEND CALL
    return http<CallTranscript>(`/job/${jobId}/company/${companyId}/transcript`);
  }
  return delay(mockTranscript(companyId), 500);
}

// ===========================================================================
// MOCK DATA GENERATORS — everything below exists only so the app runs before
// the backend is ready. Safe to delete once NEXT_PUBLIC_USE_MOCKS=false.
// ===========================================================================

function mockJobSpec(jobId: string): JobSpec {
  return {
    jobId,
    status: "ready_for_review",
    cleaningType: "Deep Cleaning",
    houseSizeSqft: 2200,
    bedrooms: 4,
    bathrooms: 3,
    furniture: ["Sofa", "Dining Table", "Wardrobe", "King Bed", "TV Console"],
    specialNotes: "Kitchen cleaning needs extra attention around the stove hood.",
    sourceFileName: "cleaning-spec.pdf",
  };
}

const MOCK_COMPANIES: Omit<CompanyCall, "status" | "price">[] = [
  { companyId: "c1", companyName: "ABC Cleaning", phone: "+1 415 555 0142" },
  { companyId: "c2", companyName: "Spark Clean", phone: "+1 415 555 0198" },
  { companyId: "c3", companyName: "Fresh Home", phone: "+1 415 555 0176" },
  { companyId: "c4", companyName: "Home Care Co.", phone: "+1 415 555 0133" },
  { companyId: "c5", companyName: "Bright Nest", phone: "+1 415 555 0119" },
];

let progressTick = 0;
function mockProgress(jobId: string): NegotiationProgress {
  progressTick += 1;
  const completedCount = Math.min(MOCK_COMPANIES.length, Math.floor(progressTick / 2));
  const companies: CompanyCall[] = MOCK_COMPANIES.map((c, i) => {
    if (i < completedCount) {
      return { ...c, status: i === 3 ? "declined" : "completed", price: i === 3 ? null : 210 + i * 10 };
    }
    if (i === completedCount) {
      return { ...c, status: "calling", price: null };
    }
    return { ...c, status: "waiting", price: null };
  });
  return {
    jobId,
    companies,
    callsCompleted: completedCount,
    callsTotal: MOCK_COMPANIES.length,
  };
}

function mockReport(jobId: string): QuoteReport {
  const companies: CompanyCall[] = [
    { ...MOCK_COMPANIES[0], status: "completed", price: 220, travelFee: "included", extraCharges: ["Window Cleaning"], callOutcome: "Quote received" },
    { ...MOCK_COMPANIES[1], status: "completed", price: 210, travelFee: "included", extraCharges: [], callOutcome: "Quote received" },
    { ...MOCK_COMPANIES[2], status: "completed", price: 250, travelFee: "extra", extraCharges: ["Deep grout scrub"], callOutcome: "Quote received" },
    { ...MOCK_COMPANIES[3], status: "declined", price: null, callOutcome: "Declined — outside service area" },
    { ...MOCK_COMPANIES[4], status: "completed", price: 130, travelFee: "included", extraCharges: [], callOutcome: "Quote received", redFlag: true },
  ];
  const priced = companies.filter((c) => c.price != null) as (CompanyCall & { price: number })[];
  const best = priced.reduce((min, c) => (c.price < min.price ? c : min), priced[0]);
  const avg = priced.reduce((sum, c) => sum + c.price, 0) / priced.length;
  const warnings: string[] = [];
  const flagged = priced.filter((c) => c.redFlag || c.price < avg * 0.6);
  flagged.forEach((c) => {
    warnings.push(`${c.companyName}'s quote ($${c.price}) is ${Math.round((1 - c.price / avg) * 100)}% below the average. Possible red flag.`);
  });
  return {
    jobId,
    companies,
    bestQuote: best ? { companyId: best.companyId, companyName: best.companyName, price: best.price } : null,
    averagePrice: Math.round(avg),
    warnings,
  };
}

function mockTranscript(companyId: string): CallTranscript {
  const name = MOCK_COMPANIES.find((c) => c.companyId === companyId)?.companyName ?? "Company";
  return {
    companyId,
    companyName: name,
    lines: [
      { speaker: "agent", text: "Hi, this is calling on behalf of a customer looking for a deep clean quote for a 2,200 sq ft, 4-bedroom home. Do you have a moment?" },
      { speaker: "company", text: "Sure, go ahead." },
      { speaker: "agent", text: "Great — 4 bedrooms, 3 bathrooms, standard furniture, and some extra attention needed around the kitchen stove hood. What would that run?" },
      { speaker: "company", text: "For that size, we'd quote around $250, travel included." },
      { speaker: "agent", text: "We've had quotes closer to $210 for a comparable job. Is there any flexibility there?" },
      { speaker: "company", text: "We could do $220 if you book this week." },
      { speaker: "agent", text: "That works — can you confirm that's the full quote with no hidden fees?" },
      { speaker: "company", text: "Yes, $220 flat, travel included." },
    ],
  };
}

// ---------------------------------------------------------------------------
// OPTIONAL: swap polling for a live socket.
// If the backend exposes Socket.io/WebSocket for negotiation progress
// instead of a polling endpoint, replace calls to getNegotiationProgress()
// on the Negotiation page with a hook like this:
//
//   useEffect(() => {
//     const socket = io(API_BASE);
//     socket.on(`negotiation:${jobId}`, (data: NegotiationProgress) => setProgress(data));
//     return () => socket.disconnect();
//   }, [jobId]);
// ---------------------------------------------------------------------------
