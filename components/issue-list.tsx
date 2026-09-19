"use client";

import { coverageBadge } from "@/lib/catalog";
import type { GraphNode } from "@/lib/types";
import { NodeCard } from "./node-card";
import { useLaw } from "./law-provider";

export function IssueList({
  issues,
  related,
}: {
  issues: GraphNode[];
  related: Record<string, GraphNode[]>;
}) {
  const { open } = useLaw();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-medium tracking-tight">Flags</h1>
        <p className="text-[var(--muted)] mt-2 max-w-2xl leading-relaxed text-sm">
          Structural conflicts, taking-or-damage, preemption, ultra vires, integrity
          risk. Open a flag for the note; open a listed instrument for the enacted text.{" "}
          {issues.length} apply here.
        </p>
      </div>
      <div className="space-y-8">
        {issues.map((issue) => (
          <section key={issue.id} id={issue.id} className="scroll-mt-28">
            <NodeCard node={issue} />
            {related[issue.id]?.length ? (
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {related[issue.id].map((node) => (
                  <button
                    key={node.id}
                    type="button"
                    onClick={() => open(node)}
                    className="w-full text-left text-sm border border-[var(--line)] rounded-lg px-3 py-2 bg-[var(--panel)] hover:border-[var(--fg)]"
                  >
                    <div className="text-[10px] uppercase tracking-wide text-[var(--muted)]">
                      {node.type} · {coverageBadge(node)}
                    </div>
                    <div className="mt-0.5">{node.label}</div>
                    <div className="text-[11px] text-[var(--muted)] mt-1">
                      Exact text →
                    </div>
                  </button>
                ))}
              </div>
            ) : null}
          </section>
        ))}
      </div>
    </div>
  );
}
