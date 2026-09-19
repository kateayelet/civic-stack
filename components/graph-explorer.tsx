"use client";

import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { LAYER_ORDER, applies, isKnownLayer, parseProfile } from "@/lib/catalog";
import type { GraphData, GraphNode } from "@/lib/types";
import { LawBlock } from "./law-block";
import { useLaw } from "./law-provider";

function RingMap({
  data,
  profile,
  onSelect,
  selectedId,
}: {
  data: GraphData;
  profile: ReturnType<typeof parseProfile>;
  onSelect: (id: string) => void;
  selectedId: string;
}) {
  const [hover, setHover] = useState<string | null>(null);
  const layout = useMemo(() => {
    const nodes = data.nodes.filter(
      (node) => node.type !== "ParcelClass" && applies(node, profile),
    );
    const byLayer = new Map<string, GraphNode[]>();
    for (const node of nodes) {
      const layer = isKnownLayer(node.layer) ? node.layer : "city";
      byLayer.set(layer, [...(byLayer.get(layer) || []), node]);
    }
    const rings = LAYER_ORDER.filter((layer) => (byLayer.get(layer) || []).length);
    const placed: { node: GraphNode; x: number; y: number; r: number }[] = [];
    rings.forEach((layer, ringIndex) => {
      const radius = 48 + 42 * ringIndex;
      const ringNodes = byLayer.get(layer) || [];
      ringNodes.forEach((node, index) => {
        const angle = (2 * Math.PI * index) / Math.max(ringNodes.length, 1) - Math.PI / 2;
        placed.push({
          node,
          x: 520 + radius * Math.cos(angle),
          y: 520 + radius * Math.sin(angle),
          r: node.type === "Issue" ? 5.5 : node.layer === "founding" ? 8 : 3.2,
        });
      });
    });
    return { placed, cx: 520, cy: 520, rings };
  }, [data, profile]);

  const active = hover || selectedId;

  return (
    <div className="rounded-lg border border-[var(--line)] bg-[#fafaf9] overflow-hidden">
      <svg viewBox="0 0 1040 1040" className="w-full h-auto max-h-[70vh]">
        {layout.rings.map((layer, index) => (
          <circle
            key={layer}
            cx={layout.cx}
            cy={layout.cy}
            r={48 + 42 * index}
            fill="none"
            stroke="#ecece8"
          />
        ))}
        <circle cx={layout.cx} cy={layout.cy} r="18" fill="#111" />
        <text
          x={layout.cx}
          y={layout.cy + 4}
          textAnchor="middle"
          fontSize="9"
          fill="#fff"
        >
          1776
        </text>
        {layout.placed.map(({ node, x, y, r }) => (
          <circle
            key={node.id}
            cx={x}
            cy={y}
            r={active === node.id ? r + 3 : r}
            fill={node.type === "Issue" ? "#b42318" : "#111111"}
            opacity={active && active !== node.id ? 0.22 : 0.95}
            className="cursor-pointer"
            onMouseEnter={() => setHover(node.id)}
            onMouseLeave={() => setHover(null)}
            onClick={() => onSelect(node.id)}
          >
            <title>{node.label}</title>
          </circle>
        ))}
      </svg>
      <div className="p-3 text-[11px] text-[var(--muted)] border-t border-[var(--line)] flex flex-wrap gap-x-4 gap-y-1">
        <span className="inline-flex items-center gap-1">
          <i className="inline-block w-2 h-2 rounded-full bg-[var(--fg)]" />
          instrument
        </span>
        <span className="inline-flex items-center gap-1">
          <i className="inline-block w-2 h-2 rounded-full bg-[var(--flag)]" />
          flag
        </span>
        <span>inner ring = 1776</span>
      </div>
    </div>
  );
}

export function GraphExplorer({ data }: { data: GraphData }) {
  const searchParams = useSearchParams();
  const profile = parseProfile(searchParams.get("profile") ?? undefined);
  const { open } = useLaw();
  const [selectedId, setSelectedId] = useState("us:declaration");
  const byId = useMemo(() => new Map(data.nodes.map((node) => [node.id, node])), [data.nodes]);
  const selected = byId.get(selectedId);
  const path = data.reason.authority_paths[selectedId] || [];
  const edges = data.edges.filter(
    (edge) => edge.source === selectedId || edge.target === selectedId,
  );
  const applyCount = data.nodes.filter((node) => applies(node, profile)).length;

  return (
    <div className="grid gap-8 lg:grid-cols-[1.05fr_0.95fr]">
      <div>
        <h1 className="text-3xl font-medium tracking-tight mb-2">Graph</h1>
        <p className="text-sm text-[var(--muted)] mb-4">
          Rings from 1776 outward — founding, federal, state, county, city, district.
          Click a node to read the text. {applyCount} apply here.
        </p>
        <RingMap
          data={data}
          profile={profile}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />
      </div>
      <div className="space-y-4">
        {selected ? (
          <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-5">
            <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
              {selected.citation || selected.id}
            </p>
            <h2 className="text-lg font-medium mt-1">{selected.label}</h2>
            <div className="mt-4">
              <LawBlock node={selected} compact />
            </div>
            <button
              type="button"
              className="mt-4 text-sm underline underline-offset-2"
              onClick={() => open(selected)}
            >
              Expand
            </button>
          </div>
        ) : null}
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-4">
          <h2 className="text-sm font-medium mb-2">Chain to the Declaration</h2>
          <ol className="space-y-1.5">
            {path.map((id, index) => {
              const node = byId.get(id);
              return (
                <li key={id}>
                  <button
                    type="button"
                    onClick={() => {
                      if (!node) return;
                      setSelectedId(id);
                      open(node);
                    }}
                    className="text-left w-full text-sm hover:underline"
                  >
                    <span className="text-[10px] text-[var(--muted)] font-mono mr-2">
                      {index + 1}
                    </span>
                    {node?.label || id}
                  </button>
                </li>
              );
            })}
          </ol>
        </div>
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-4">
          <h2 className="text-sm font-medium mb-2">Edges</h2>
          <ul className="space-y-2 max-h-64 overflow-auto text-sm text-[var(--muted)]">
            {edges.slice(0, 40).map((edge) => (
              <li key={edge.id}>
                <button type="button" onClick={() => setSelectedId(edge.source)}>
                  {byId.get(edge.source)?.label || edge.source}
                </button>{" "}
                <span className="text-[10px] uppercase">
                  {edge.type.replace(/_/g, " ")}
                </span>{" "}
                <button type="button" onClick={() => setSelectedId(edge.target)}>
                  {byId.get(edge.target)?.label || edge.target}
                </button>
                {edge.note ? <p className="text-xs mt-0.5">{edge.note}</p> : null}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
