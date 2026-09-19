import type { GraphNode } from "@/lib/types";

const KIND_LABEL: Record<string, string> = {
  enacted: "Exact text",
  holding: "Reported holding",
  note: "Notes — not enacted text",
  catalog: "Exact text",
};

export function LawBlock({
  node,
  compact = false,
}: {
  node: GraphNode;
  compact?: boolean;
}) {
  const kind = node.text_kind || (node.type === "Issue" ? "note" : "enacted");
  const text = (node.text || "").trim();
  const summary = (node.summary || "").trim();
  const hasExact = kind === "enacted" || kind === "holding";
  const showNotes = !!summary && summary !== text;

  const coverageSuffix =
    node.coverage === "excerpt"
      ? " · excerpt"
      : node.coverage === "full"
        ? " · full"
        : kind === "catalog"
          ? " · not ingested"
          : "";

  return (
    <div className="space-y-6">
      {kind === "note" ? (
        <div>
          <p className="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)] mb-2">
            Notes — not enacted text
          </p>
          <p className="text-sm leading-relaxed text-[var(--fg)]">
            {summary || text}
          </p>
          {node.text_source ? (
            <p className="text-[11px] text-[var(--muted)] mt-3">{node.text_source}</p>
          ) : null}
        </div>
      ) : (
        <div>
          <div className="flex flex-wrap items-baseline justify-between gap-2 mb-3">
            <p className="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">
              {KIND_LABEL[kind] || "Exact text"}
              {coverageSuffix}
            </p>
            {node.url ? (
              <a
                href={node.url}
                target="_blank"
                rel="noreferrer"
                className="text-[11px] underline underline-offset-2 text-[var(--muted)] hover:text-[var(--fg)]"
              >
                Official source
              </a>
            ) : null}
          </div>
          {hasExact && text ? (
            <article
              className={`whitespace-pre-wrap leading-[1.65] text-[var(--fg)] font-serif ${
                compact ? "text-sm max-h-64 overflow-auto" : "text-[15px] md:text-[16px]"
              }`}
            >
              {text}
            </article>
          ) : null}
          {kind === "catalog" ? (
            <div className="space-y-2">
              {node.citation ? (
                <p className="text-xs font-mono text-[var(--muted)]">{node.citation}</p>
              ) : null}
              <p className="text-[15px] leading-snug">{node.label}</p>
              <p className="text-sm text-[var(--muted)] leading-relaxed">
                The enacted body of this section is not in this corpus. The official
                publisher controls.
              </p>
            </div>
          ) : null}
          {hasExact && node.text_source ? (
            <p className="text-[11px] text-[var(--muted)] mt-3">{node.text_source}</p>
          ) : null}
        </div>
      )}
      {kind !== "note" && showNotes ? (
        <div className="border-t border-[var(--line)] pt-4">
          <p className="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)] mb-2">
            Notes
          </p>
          <p className="text-sm text-[var(--muted)] leading-relaxed">{summary}</p>
        </div>
      ) : null}
    </div>
  );
}
