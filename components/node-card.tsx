"use client";

import { coverageBadge } from "@/lib/catalog";
import type { GraphNode } from "@/lib/types";
import { useLaw } from "./law-provider";

function Badge({
  children,
  kind,
}: {
  children: string;
  kind?: string;
}) {
  const flagged =
    kind && kind !== "catalog" && kind !== "enacted" && kind !== "heading";
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wide ${
        flagged
          ? "border-red-200 text-[var(--flag)] bg-red-50"
          : "border-[var(--line)] text-[var(--muted)]"
      }`}
    >
      {children.replace(/_/g, " ")}
    </span>
  );
}

export function NodeCard({
  node,
  depth,
}: {
  node: GraphNode;
  depth?: number;
}) {
  const { open } = useLaw();
  const kind = node.text_kind || (node.type === "Issue" ? "note" : "enacted");
  const raw =
    kind === "catalog"
      ? ""
      : (node.text || node.summary || "").replace(/\s+/g, " ").trim();
  const excerpt = raw.length > 220 ? `${raw.slice(0, 220)}…` : raw;
  const serif = kind === "enacted" || kind === "holding";

  return (
    <button
      type="button"
      onClick={() => open(node)}
      className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-4 text-left hover:border-[var(--fg)] transition-colors h-full w-full"
    >
      <div className="flex flex-wrap gap-1.5 mb-2">
        <Badge>{node.type}</Badge>
        {node.kind ? <Badge kind={node.kind}>{node.kind}</Badge> : null}
        {node.severity ? <Badge kind="taking">{node.severity}</Badge> : null}
        <Badge>{coverageBadge(node)}</Badge>
        {typeof depth === "number" ? <Badge>{`${depth} hops`}</Badge> : null}
      </div>
      <h3 className="text-base font-medium leading-snug">{node.label}</h3>
      {node.citation ? (
        <p className="text-[11px] font-mono text-[var(--muted)] mt-1">{node.citation}</p>
      ) : null}
      {excerpt ? (
        <p
          className={`text-sm mt-3 leading-relaxed ${
            serif ? "font-serif text-[var(--fg)]" : "text-[var(--muted)]"
          }`}
        >
          {excerpt}
        </p>
      ) : (
        <p className="text-sm text-[var(--muted)] mt-3 leading-relaxed">
          Heading only — open for the official source.
        </p>
      )}
      <p className="text-[11px] text-[var(--muted)] mt-3">Exact text →</p>
    </button>
  );
}
