"use client";

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
  const filtered =
    band === "all"
      ? nodes
      : nodes.filter((node) => {
          const match = BANDS.find((item) => item.id === band);
          return match ? match.layers.includes(node.layer) : true;
        });

  const grouped = BANDS.map((item) => ({
    ...item,
    rows: filtered
      .filter((node) => item.layers.includes(node.layer))
      .slice()
      .sort((a, b) => a.label.localeCompare(b.label)),
  })).filter((item) => item.rows.length);

  return (
    <div className="space-y-6" data-band={band} data-rows={filtered.length}>
      <div>
        <h1 className="text-3xl font-medium tracking-tight">Laws at this house</h1>
        <p className="text-[var(--muted)] mt-2 max-w-2xl text-sm leading-relaxed">
          Every founding, federal, state, county, city, and district instrument in this
          corpus that binds the selected 94920 profile. Open a row for the exact text.
          Showing {filtered.length} of {nodes.length}.{note}
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
      {grouped.map((group) => (
        <section key={group.id} className="space-y-2">
          <h2 className="text-xl font-medium">
            {group.label}{" "}
            <span className="text-[var(--muted)] text-base">{group.rows.length}</span>
          </h2>
          <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] overflow-hidden">
            {group.rows.map((node) => (
              <button
                key={node.id}
                type="button"
                onClick={() => open(node)}
                className="w-full text-left px-3 py-2.5 hover:bg-[var(--bg)] flex items-start gap-3 border-b border-[var(--line)] last:border-b-0"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm leading-snug">{node.label}</p>
                  <p className="text-[11px] font-mono text-[var(--muted)] mt-0.5 truncate">
                    {node.citation}
                  </p>
                </div>
                <span className="shrink-0 text-[10px] uppercase tracking-wide text-[var(--muted)] mt-0.5">
                  {coverageBadge(node)}
                </span>
              </button>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
