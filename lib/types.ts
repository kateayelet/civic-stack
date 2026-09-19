export type ProfileId = "tiburon" | "belvedere" | "paradise_cay" | "strawberry";

export type NodeType =
  | "Actor"
  | "Instrument"
  | "Provision"
  | "Jurisdiction"
  | "ParcelClass"
  | "Issue";

export type TextKind = "enacted" | "catalog" | "holding" | "note";

export type Coverage = "full" | "excerpt" | "catalog" | "holding";

export interface GraphNode {
  id: string;
  type: NodeType;
  label: string;
  layer: string;
  citation: string;
  summary: string;
  text: string;
  url: string;
  jurisdiction: string;
  year: string;
  topics: string[];
  applies_to: string[];
  coverage: Coverage | string;
  flags: string[];
  text_kind: TextKind | string;
  text_source: string;
  kind?: string;
  severity?: string;
  status?: string;
  applicability?: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  note: string;
  confidence: string;
  evidence: string;
}

export interface ProfileSlice {
  id: string;
  node_count: number;
  issue_count: number;
  nodes: string[];
  issues: string[];
}

export interface GraphReason {
  authority_paths: Record<string, string[]>;
  depth_from_declaration: Record<string, number>;
  orphans?: unknown[];
  cycles?: unknown[];
  conflict_count?: number;
  taking_edge_count?: number;
  issue_count?: number;
}

export interface GraphData {
  meta: {
    name: string;
    zip: string;
    compiled_at: string;
    disclaimer: string;
    form: string;
    node_count: number;
    edge_count: number;
  };
  nodes: GraphNode[];
  edges: GraphEdge[];
  profiles: Record<string, ProfileSlice>;
  reason: GraphReason;
  issues: GraphNode[];
  conflicts: GraphEdge[];
  takings: GraphEdge[];
}

export interface ProfileMeta {
  title: string;
  sovereign: string;
  blurb: string;
}

export interface Band {
  id: string;
  label: string;
  layers: string[];
}
