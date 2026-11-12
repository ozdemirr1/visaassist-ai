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

export interface DocumentInfo {
  id: string;
  application_file_id: string;
  requirement_id: string;
  document_type_id: string;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  uploaded_at: string;
  delete_after: string;
}

export interface ConsentState {
  version: string;
  given: boolean;
}

export type FieldType = "text" | "date" | "int" | "bool" | "money" | "language";
export interface Money {
  amount: number;
  currency: string;
}
export type FieldValue = string | number | boolean | Money | null;

export interface FieldInfo {
  id: string;
  type: FieldType;
  title: string;
  optional: boolean;
  value: FieldValue;
}

export interface DocumentFields {
  document_id: string;
  document_type_id: string;
  fields: FieldInfo[];
}

export type RuleStatus = "passed" | "failed" | "incomplete" | "skipped";

export interface CheckIssue {
  code: string;
  document_id: string | null;
  document_type: string | null;
  document_title: string | null;
  field: string | null;
  field_title: string | null;
  value: unknown;
  expected: unknown;
}

export interface RuleResult {
  rule_id: string;
  severity: "error" | "warning";
  status: RuleStatus;
  issues: CheckIssue[];
}

export interface CheckResult {
  requirement_set_id: string;
  missing_documents: string[];
  rules: RuleResult[];
  summary: Record<RuleStatus | "missing_documents", number>;
}
