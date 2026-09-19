import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { GraphData, GraphNode, ProfileId } from "./types";
import { BANDS, applies } from "./catalog";

const dataDir = join(process.cwd(), "data");

function readJson<T>(name: string): T {
  return JSON.parse(readFileSync(join(dataDir, name), "utf8")) as T;
}

const graph = readJson<GraphData>("graph.json");
const issueNodes = readJson<GraphNode[]>("issues.json");

const corpora: Record<ProfileId, GraphNode[]> = {
  tiburon: readJson<GraphNode[]>("corpus_tiburon.json"),
  belvedere: readJson<GraphNode[]>("corpus_belvedere.json"),
  paradise_cay: readJson<GraphNode[]>("corpus_paradise_cay.json"),
  strawberry: readJson<GraphNode[]>("corpus_strawberry.json"),
};

export function getGraph(): GraphData {
  return graph;
}

export function getIssues(): GraphNode[] {
  return issueNodes;
}

export function lawsForProfile(profile: ProfileId): GraphNode[] {
  return corpora[profile];
}

export function issuesForProfile(profile: ProfileId): GraphNode[] {
  return issueNodes.filter((node) => applies(node, profile));
}

export function highSeverityIssues(profile: ProfileId): GraphNode[] {
  return issuesForProfile(profile).filter((node) => node.severity === "high");
}

export function bandCounts(nodes: GraphNode[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const band of BANDS) {
    counts[band.id] = nodes.filter((node) => band.layers.includes(node.layer)).length;
  }
  return counts;
}

export function flaggedTargets(issueId: string, profile: ProfileId): GraphNode[] {
  const byId = new Map(graph.nodes.map((node) => [node.id, node]));
  return graph.edges
    .filter((edge) => edge.type === "FLAGS" && edge.source === issueId)
    .map((edge) => byId.get(edge.target))
    .filter((node): node is GraphNode => !!node && applies(node, profile));
}
