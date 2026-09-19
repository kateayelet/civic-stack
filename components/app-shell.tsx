"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { PROFILE_IDS, PROFILE_META, parseProfile } from "@/lib/catalog";

const NAV = [
  { href: "/", label: "Home" },
  { href: "/graph", label: "Graph" },
  { href: "/chain", label: "Chain" },
  { href: "/issues", label: "Flags" },
  { href: "/corpus", label: "Laws" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const profile = parseProfile(searchParams.get("profile") ?? undefined);

  const withProfile = (href: string) => {
    const params = new URLSearchParams();
    params.set("profile", profile);
    return `${href}?${params.toString()}`;
  };

  return (
    <div className="min-h-screen">
      <header className="border-b border-[var(--line)] bg-[var(--panel)]/90 backdrop-blur sticky top-0 z-40">
        <div className="mx-auto max-w-6xl px-4 py-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <Link
              href={withProfile("/")}
              className="text-[15px] font-medium tracking-tight"
            >
              94920
            </Link>
            <p className="text-xs text-[var(--muted)] mt-0.5">
              Exact text · authority chain
            </p>
          </div>
          <nav className="flex flex-wrap gap-1">
            {NAV.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={withProfile(item.href)}
                  className={`px-3 py-1.5 rounded-full text-sm ${
                    active
                      ? "bg-[var(--fg)] text-white"
                      : "text-[var(--muted)] hover:text-[var(--fg)]"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="border-t border-[var(--line)]">
          <div className="mx-auto max-w-6xl px-4 py-2 flex gap-2 overflow-x-auto">
            {PROFILE_IDS.map((id) => {
              const params = new URLSearchParams(searchParams.toString());
              params.set("profile", id);
              const href = `${pathname}?${params.toString()}`;
              const active = profile === id;
              return (
                <Link
                  key={id}
                  href={href}
                  className={`shrink-0 px-3 py-1 rounded-full text-xs md:text-sm ${
                    active
                      ? "bg-[var(--fg)] text-white"
                      : "text-[var(--muted)] hover:text-[var(--fg)]"
                  }`}
                >
                  {PROFILE_META[id].title}
                </Link>
              );
            })}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 md:py-12">{children}</main>
      <footer className="border-t border-[var(--line)] px-4 py-6 text-xs text-[var(--muted)] mx-auto max-w-6xl">
        Not legal advice. Official publishers control. Each point opens the exact
        text first; notes are labeled separately.
      </footer>
    </div>
  );
}
