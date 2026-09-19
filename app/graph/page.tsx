import { Suspense } from "react";
import { GraphExplorer } from "@/components/graph-explorer";
import { getGraph } from "@/lib/data";

export default function GraphPage() {
  const data = getGraph();
  return (
    <Suspense
      fallback={
        <p className="text-[var(--muted)] text-sm">Loading graph…</p>
      }
    >
      <GraphExplorer data={data} />
    </Suspense>
  );
}
