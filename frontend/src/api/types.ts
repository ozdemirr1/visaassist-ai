// Response shapes of the backend API (backend/app/api/*.py).

export type Language = "tr" | "en";
export type Profile = "employed" | "student";

export interface Citation {
  source_id: string;
  title: string;
  publisher: string;
  url: string;
  section: string;
  passage: string;
  basis: "stated" | "derived";
}

export interface ChecklistItem {
  id: string;
  layer: "eu" | "national";
  document: { id: string; title: string; multiple: boolean };
  submit_as: string;
  note: string | null;
  source: Citation;
}

export interface RuleSummary {
  id: string;
  title: string;
  severity: "error" | "warning";
  kind: string;
  source: Citation;
}

export interface Checklist {
  requirement_set_id: string;
  destination: string;
  profile: Profile;
  language: Language;
  items: ChecklistItem[];
  rules: RuleSummary[];
  translation: { required: boolean; languages: string[] };
}

export interface User {
  id: string;
  email: string;
  role: "applicant" | "admin";
  language: Language;
}

export type Step = "draft" | "appointment" | "documents" | "submitted" | "decided";

export interface ApplicationFile {
  id: string;
  destination: string;
  visa: string;
  purpose: string;
  profile: Profile;
  trip_start: string;
  trip_end: string;
  application_date: string;
  step: Step;
  requirement_set_id: string;
  created_at: string;
  events: { step: Step; occurred_at: string }[];
}
