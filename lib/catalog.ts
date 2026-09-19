import type { Band, GraphNode, ProfileId, ProfileMeta } from "./types";

export const DEFAULT_PROFILE: ProfileId = "tiburon";

export const PROFILE_IDS: ProfileId[] = [
  "belvedere",
  "tiburon",
  "paradise_cay",
  "strawberry",
];

export const PROFILE_META: Record<ProfileId, ProfileMeta> = {
  belvedere: {
    title: "City of Belvedere",
    sovereign: "Belvedere Municipal Code",
    blurb:
      "Island and lagoon. Own city hall, planning, building, and police. General-law city since 1896.",
  },
  tiburon: {
    title: "Town of Tiburon",
    sovereign: "Tiburon Code of Ordinances",
    blurb:
      "Peninsula town since 1964. Agins was litigated against this government. SPAR design review plus a view-from-trees ordinance.",
  },
  paradise_cay: {
    title: "Paradise Cay / CSA 29",
    sovereign: "Marin County Code (not Tiburon)",
    blurb:
      "Unincorporated canal lots. County building and zoning. CSA 29 dredges. Surrounded by Tiburon, not governed by it.",
  },
  strawberry: {
    title: "Unincorporated Strawberry pocket",
    sovereign: "Marin County Code",
    blurb:
      "North-peninsula unincorporated land in the same ZIP. County Title 22 and often Richardson Bay Sanitary.",
  },
};

export const LAYER_ORDER = [
  "founding",
  "treaty",
  "federal-constitution",
  "federal-statute",
  "federal-regulation",
  "federal-case",
  "state-constitution",
  "state-statute",
  "state-regulation",
  "state-case",
  "county",
  "city",
  "district",
  "private",
  "issue",
] as const;

export const BANDS: Band[] = [
  { id: "founding", label: "Founding", layers: ["founding", "treaty"] },
  {
    id: "federal",
    label: "Federal",
    layers: [
      "federal-constitution",
      "federal-statute",
      "federal-regulation",
      "federal-case",
    ],
  },
  {
    id: "state",
    label: "State",
    layers: [
      "state-constitution",
      "state-statute",
      "state-regulation",
      "state-case",
    ],
  },
  { id: "county", label: "County", layers: ["county"] },
  { id: "city", label: "City", layers: ["city"] },
  { id: "district", label: "District", layers: ["district"] },
  { id: "private", label: "Private", layers: ["private"] },
];

export function isProfileId(value: string | undefined | null): value is ProfileId {
  return !!value && (PROFILE_IDS as string[]).includes(value);
}

export function parseProfile(value: string | string[] | undefined): ProfileId {
  const raw = Array.isArray(value) ? value[0] : value;
  return isProfileId(raw) ? raw : DEFAULT_PROFILE;
}

export function applies(node: GraphNode, profile: ProfileId): boolean {
  const list = node.applies_to;
  if (!list?.length || list.includes("all")) return true;
  return list.includes(profile);
}

export function isLaw(node: GraphNode): boolean {
  return (
    node.type === "Instrument" ||
    node.type === "Provision" ||
    node.type === "Jurisdiction"
  );
}

export function bandOf(layer: string): Band | undefined {
  return BANDS.find((band) => band.layers.includes(layer));
}

export function isKnownLayer(layer: string): boolean {
  return (LAYER_ORDER as readonly string[]).includes(layer);
}

export function coverageBadge(node: GraphNode): string {
  const kind = node.text_kind || (node.type === "Issue" ? "note" : "enacted");
  if (kind === "catalog") return "heading";
  return kind;
}

export function corpusNote(profile: ProfileId): string {
  if (profile === "tiburon" || profile === "belvedere") {
    return " Marin Title 22 does not zone this incorporated parcel; county tax and the state/federal stack still do.";
  }
  return " This unincorporated parcel is zoned by Marin County, not by Tiburon or Belvedere.";
}

export function withProfile(href: string, profile: ProfileId): string {
  const url = new URL(href, "https://civic.ink");
  url.searchParams.set("profile", profile);
  return `${url.pathname}?${url.searchParams.toString()}`;
}
