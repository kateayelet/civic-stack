"use client";

import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { BANDS, applies, bandOf, isLaw, parseProfile } from "@/lib/catalog";
import type { GraphData } from "@/lib/types";
import { LawBlock } from "./law-block";
import { useLaw } from "./law-provider";

export function ChainExplorer({ data }: { data: GraphData }) {
  const searchParams = useSearchParams();
  const profile = parseProfile(searchParams.get("profile") ?? undefined);
  const { open } = useLaw();
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState("us:const:am-v");
  const byId = useMemo(() => new Map(data.nodes.map((node) => [node.id, node])), [data.nodes]);

  const matches = useMemo(() => {
    const laws = data.nodes.filter((node) => isLaw(node) && applies(node, profile));
    const needle = query.trim().toLowerCase();
    if (!needle) {
      const preview: typeof laws = [];
      for (const band of BANDS) {
        preview.push(
          ...laws
            .filter((node) => band.layers.includes(node.layer))
            .sort((a, b) => a.label.localeCompare(b.label))
            .slice(0, 6),
        );
      }
      return preview;
    }
    return laws
      .filter((node) =>
        `${node.label} ${node.citation} ${node.summary} ${node.text || ""} ${node.id} ${node.layer}`
          .toLowerCase()
          .includes(needle),
      )
      .slice(0, 80);
  }, [data.nodes, profile, query]);

  const path = data.reason.authority_paths[selectedId] || [selectedId];
  const selected = byId.get(selectedId);
  const conflicts = data.edges.filter(
    (edge) =>
      edge.type === "CONFLICTS_WITH" &&
      (path.includes(edge.source) ||
        path.includes(edge.target) ||
        edge.source === selectedId ||
        edge.target === selectedId),
  );
  const takings = data.edges.filter(
    (edge) =>
      edge.type === "TAKES_OR_BURDENS" &&
      (edge.source === selectedId ||
        edge.target === selectedId ||
        path.includes(edge.source)),
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-medium tracking-tight">Authority chain</h1>
        <p className="text-[var(--muted)] mt-2 max-w-2xl text-sm">
          Search federal, state, county, city, or district law. The text is first; notes
          are labeled. Then walk the grant to the Declaration.
        </p>
      </div>
      <input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search 1983, Prop 13, Title 22, ADU, BCDC, view…"
        className="w-full rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3 outline-none focus:border-[var(--fg)]"
      />
      <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <ul className="space-y-1 max-h-[70vh] overflow-auto">
          {matches.map((node) => (
            <li key={node.id}>
              <button
                type="button"
                onClick={() => setSelectedId(node.id)}
                className={`w-full text-left rounded-lg px-3 py-2 border ${
                  selectedId === node.id
                    ? "border-[var(--fg)] bg-[var(--panel)]"
                    : "border-transparent hover:border-[var(--line)]"
                }`}
              >
                <div className="text-[10px] uppercase tracking-wide text-[var(--muted)]">
                  {bandOf(node.layer)?.label || node.layer}
                </div>
                <div className="text-sm">{node.label}</div>
                <div className="text-[11px] font-mono text-[var(--muted)]">
                  {node.citation || node.id}
                </div>
              </button>
            </li>
          ))}
        </ul>
        <div className="space-y-4">
          {selected ? (
            <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-5">
              <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
                {data.reason.depth_from_declaration[selected.id] ?? "—"} hops from the
                Declaration
              </p>
              <h2 className="text-xl font-medium mt-1">{selected.label}</h2>
              <p className="text-xs font-mono text-[var(--muted)] mt-1">
                {selected.citation}
              </p>
              <div className="mt-5">
                <LawBlock node={selected} />
              </div>
            </div>
          ) : null}
          <ol className="relative border-l border-[var(--line)] ml-3 space-y-4">
            {path.map((id, index) => {
              const node = byId.get(id);
              const founding = index === path.length - 1;
              return (
                <li key={id} className="pl-6">
                  <span className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full bg-[var(--fg)]" />
                  <button
                    type="button"
                    onClick={() => {
                      if (!node) return;
                      setSelectedId(id);
                      open(node);
                    }}
                    className="text-left"
                  >
                    <p className="text-[11px] uppercase tracking-wide text-[var(--muted)]">
                      {founding ? "Founding" : node?.layer}
                    </p>
                    <p className="text-base font-medium">{node?.label || id}</p>
                  </button>
                </li>
              );
            })}
          </ol>
          {conflicts.length ? (
            <div className="rounded-lg border border-red-200 p-4">
              <h2 className="text-sm font-medium text-[var(--flag)]">Contradictions</h2>
              <ul className="mt-2 space-y-2 text-sm">
                {conflicts.map((edge) => (
                  <li key={edge.id}>
                    {byId.get(edge.source)?.label} ↔ {byId.get(edge.target)?.label}
                    {edge.note ? (
                      <span className="block text-[var(--muted)]">{edge.note}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {takings.length ? (
            <div className="rounded-lg border border-amber-200 p-4">
              <h2 className="text-sm font-medium">Taking-or-burden</h2>
              <ul className="mt-2 space-y-2 text-sm">
                {takings.map((edge) => (
                  <li key={edge.id}>
                    {byId.get(edge.source)?.label} → {byId.get(edge.target)?.label}
                    {edge.note ? (
                      <span className="block text-[var(--muted)]">{edge.note}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
