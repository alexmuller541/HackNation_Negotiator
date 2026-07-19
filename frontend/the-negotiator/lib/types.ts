// ---------------------------------------------------------------------------
// Shared types for The Negotiator frontend.
// These mirror the JSON shapes the backend team is expected to return.
// If the real API differs, this is the single file to edit — every
// page/component imports its shapes from here.
// ---------------------------------------------------------------------------

export type JobStatus =
  | "uploaded"
  | "extracting"
  | "ready_for_review"
  | "confirmed"
  | "negotiating"
  | "completed";

export interface JobSpec {
  jobId: string;
  status: JobStatus;
  cleaningType: string;
  houseSizeSqft: number;
  bedrooms: number;
  bathrooms: number;
  furniture: string[];
  specialNotes: string;
  sourceFileName?: string;
}

export type CallStatus = "waiting" | "calling" | "completed" | "declined" | "failed";

export interface CompanyCall {
  companyId: string;
  companyName: string;
  phone?: string;
  status: CallStatus;
  price: number | null;
  travelFee?: "included" | "extra" | null;
  extraCharges?: string[];
  callOutcome?: string;
  redFlag?: boolean;
  startedAt?: string;
  completedAt?: string;
}

export interface NegotiationProgress {
  jobId: string;
  companies: CompanyCall[];
  callsCompleted: number;
  callsTotal: number;
}

export interface QuoteReport {
  jobId: string;
  companies: CompanyCall[];
  bestQuote: { companyId: string; companyName: string; price: number } | null;
  averagePrice: number | null;
  warnings: string[];
}

export interface TranscriptLine {
  speaker: "agent" | "company";
  text: string;
  timestamp?: string;
}

export interface CallTranscript {
  companyId: string;
  companyName: string;
  lines: TranscriptLine[];
}
