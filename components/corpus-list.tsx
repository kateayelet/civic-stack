"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { BANDS, coverageBadge, withProfile } from "@/lib/catalog";
import type { GraphNode, ProfileId } from "@/lib/types";
import { useLaw } from "./law-provider";

export function CorpusList({
  profile,
  band,
  nodes,
  note,
}: {
  profile: ProfileId;
  band: string;
  nodes: GraphNode[];
  note: string;
}) {
  const { open } = useLaw();
  const [query, setQuery] = useState("");

  const scoped = useMemo(() => {
    const inBand =
      band === "all"
        ? nodes
        : nodes.filter((node) => {
            const match = BANDS.find((item) => item.id === band);
            return match ? match.layers.includes(node.layer) : true;
          });
    const needle = query
      .trim()
      .toLowerCase()
      .replace(/\bprop\s*13\b/g, "proposition 13");
    if (!needle) return inBand;
    return inBand.filter((node) =>
      `${node.label} ${node.citation} ${node.summary} ${node.text || ""} ${node.id} ${node.layer}`
        .toLowerCase()
        .replace(/\bprop\s*13\b/g, "proposition 13")
        .includes(needle),
    );
  }, [band, nodes, query]);

  const grouped = BANDS.map((item) => ({
    ...item,
    rows: scoped
      .filter((node) => item.layers.includes(node.layer))
      .slice()
      .sort((a, b) => a.label.localeCompare(b.label)),
  })).filter((item) => item.rows.length);

  return (
    <div className="space-y-6" data-band={band} data-rows={scoped.length}>
      <div>
        <h1 className="text-3xl font-medium tracking-tight">Laws at this house</h1>
        <p className="text-[var(--muted)] mt-2 max-w-2xl text-sm leading-relaxed">
          Every founding, federal, state, county, city, and district instrument in this
          corpus that binds the selected 94920 profile. Open a row for the exact text.
          Showing {scoped.length} of {nodes.length}.{note}
        </p>
      </div>
      <div className="flex flex-wrap gap-1.5">
        <Link
          href={withProfile("/corpus", profile)}
          className={`px-3 py-1.5 rounded-full text-sm ${
            band === "all"
              ? "bg-[var(--fg)] text-white"
              : "text-[var(--muted)] hover:text-[var(--fg)] border border-[var(--line)]"
          }`}
        >
          All {nodes.length}
        </Link>
        {BANDS.map((item) => {
          const count = nodes.filter((node) => item.layers.includes(node.layer)).length;
          return (
            <Link
              key={item.id}
              href={withProfile(`/corpus?band=${item.id}`, profile)}
              className={`px-3 py-1.5 rounded-full text-sm ${
                band === item.id
                  ? "bg-[var(--fg)] text-white"
                  : "text-[var(--muted)] hover:text-[var(--fg)] border border-[var(--line)]"
              }`}
            >
              {item.label} {count}
            </Link>
          );
        })}
      </div>
      <input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Filter ADU, Prop 13, 1983, Title 22, BCDC, flood…"
        className="w-full rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-2 outline-none focus:border-[var(--fg)]"
      />
      <div className="space-y-8">
        {grouped.map((group) => (
          <section key={group.id} id={group.id}>
            <div className="flex items-baseline justify-between gap-3 mb-2 sticky top-[7.5rem] bg-[var(--bg)] py-2 z-10">
              <h2 className="text-lg font-medium">{group.label}</h2>
              <p className="text-xs text-[var(--muted)]">{group.rows.length}</p>
            </div>
            <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] divide-y divide-[var(--line)]">
              {group.rows.map((node) => {
                const badge = coverageBadge(node);
                return (
                  <button
                    key={node.id}
                    type="button"
                    onClick={() => open(node)}
                    className="w-full text-left px-3 py-2.5 hover:bg-[var(--bg)] flex items-start gap-3"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm leading-snug">{node.label}</p>
                      <p className="text-[11px] font-mono text-[var(--muted)] mt-0.5 truncate">
                        {node.citation}
                      </p>
                    </div>
                    <span className="shrink-0 text-[10px] uppercase tracking-wide text-[var(--muted)] mt-0.5">
                      {badge === "enacted" ? "text" : badge}
                    </span>
                  </button>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
