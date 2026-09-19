import { Suspense } from "react";
import { ChainExplorer } from "@/components/chain-explorer";
import { getGraph } from "@/lib/data";

export default function ChainPage() {
  const data = getGraph();
  return (
    <Suspense
      fallback={
        <p className="text-[var(--muted)] text-sm">Loading chains…</p>
      }
    >
      <ChainExplorer data={data} />
    </Suspense>
  );
}
