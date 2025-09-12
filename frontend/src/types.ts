export type EvidenceHighlight = { start: number; end: number };

export type OverviewCitation = {
  id: string;
  chunk_id: string;
  page: number;
  section_path: string;
  evidence_type?: string;
  score: number;
  highlights: EvidenceHighlight[];
  text?: string;
};

export type OverviewSection = { text: string; citation_ids: string[] };

export type Overview = {
  overview_markdown: string;
  purpose: OverviewSection;
  scope: OverviewSection;
  key_requirements: OverviewSection[];
  effective_dates: OverviewSection[];
  amendments: OverviewSection[];
  affected_parties: OverviewSection;
  citations: OverviewCitation[];
};
