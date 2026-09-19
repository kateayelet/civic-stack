"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { GraphNode } from "@/lib/types";
import { LawBlock } from "./law-block";

type LawContextValue = {
  open: (node: GraphNode) => void;
  close: () => void;
};

const LawContext = createContext<LawContextValue>({
  open: () => {},
  close: () => {},
});

export function useLaw() {
  return useContext(LawContext);
}

function LawDrawer({
  node,
  onClose,
}: {
  node: GraphNode;
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        type="button"
        aria-label="Close"
        className="absolute inset-0 bg-black/15"
        onClick={onClose}
      />
      <aside className="relative h-full w-full max-w-xl bg-[var(--panel)] border-l border-[var(--line)] overflow-y-auto">
        <div className="sticky top-0 bg-[var(--panel)] border-b border-[var(--line)] px-6 md:px-8 py-4 flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">
              {node.type} · {node.layer}
            </p>
            <h2 className="text-lg mt-1 leading-snug font-medium">{node.label}</h2>
            {node.citation ? (
              <p className="text-xs font-mono text-[var(--muted)] mt-1 truncate">
                {node.citation}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 text-sm text-[var(--muted)] hover:text-[var(--fg)]"
          >
            Close
          </button>
        </div>
        <div className="px-6 md:px-8 py-6">
          <LawBlock node={node} />
        </div>
      </aside>
    </div>
  );
}

export function LawProvider({ children }: { children: React.ReactNode }) {
  const [node, setNode] = useState<GraphNode | null>(null);
  const close = useCallback(() => setNode(null), []);
  const value = useMemo(() => ({ open: setNode, close }), [close]);

  return (
    <LawContext.Provider value={value}>
      {children}
      {node ? <LawDrawer node={node} onClose={close} /> : null}
    </LawContext.Provider>
  );
}
