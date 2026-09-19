import Link from "next/link";
import { NodeCard } from "@/components/node-card";
import { BANDS, PROFILE_META, parseProfile, withProfile } from "@/lib/catalog";
import {
  bandCounts,
  highSeverityIssues,
  lawsForProfile,
  issuesForProfile,
} from "@/lib/data";

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ profile?: string }>;
}) {
  const params = await searchParams;
  const profile = parseProfile(params.profile);
  const meta = PROFILE_META[profile];
  const laws = lawsForProfile(profile);
  const issues = issuesForProfile(profile);
  const highs = highSeverityIssues(profile);
  const counts = bandCounts(laws);

  return (
    <div className="space-y-10">
      <section className="grid gap-10 lg:grid-cols-[1.15fr_0.85fr] items-start">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
            ZIP 94920 · Marin County
          </p>
          <h1 className="text-4xl md:text-5xl mt-3 leading-[1.08] font-medium tracking-tight text-[var(--fg)]">
            The law that claims the house.
          </h1>
          <p className="mt-4 text-[var(--muted)] text-base md:text-lg leading-relaxed max-w-xl">
            One ZIP, three governments. Federal, state, county, city, and district law
            all bind the same house. Open any point for the enacted text, then walk the
            grant back to the Declaration.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href={withProfile("/corpus", profile)}
              className="rounded-full bg-[var(--fg)] text-white px-5 py-2 text-sm"
            >
              All laws at this house
            </Link>
            <Link
              href={withProfile("/chain", profile)}
              className="rounded-full border border-[var(--line)] px-5 py-2 text-sm"
            >
              Trace a chain
            </Link>
          </div>
        </div>
        <aside className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-5 space-y-3">
          <p className="text-xs uppercase tracking-[0.16em] text-[var(--muted)]">
            Parcel
          </p>
          <h2 className="text-xl font-medium">{meta.title}</h2>
          <p className="text-sm text-[var(--muted)] leading-relaxed">{meta.blurb}</p>
          <p className="text-xs font-mono text-[var(--muted)]">{meta.sovereign}</p>
          <dl className="grid grid-cols-2 gap-3 pt-2 text-sm">
            <div>
              <dt className="text-[var(--muted)] text-xs">Laws here</dt>
              <dd className="text-2xl font-medium">{laws.length}</dd>
            </div>
            <div>
              <dt className="text-[var(--muted)] text-xs">Flags</dt>
              <dd className="text-2xl font-medium">{issues.length}</dd>
            </div>
          </dl>
        </aside>
      </section>

      <section>
        <div className="flex items-end justify-between gap-4 mb-4">
          <h2 className="text-xl font-medium">The stack on this parcel</h2>
          <Link
            href={withProfile("/corpus", profile)}
            className="text-sm text-[var(--muted)] hover:text-[var(--fg)]"
          >
            See every law →
          </Link>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {BANDS.map((band) => (
            <Link
              key={band.id}
              href={withProfile(`/corpus?band=${band.id}`, profile)}
              className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-4 hover:border-[var(--fg)]"
            >
              <p className="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">
                {band.label}
              </p>
              <p className="text-2xl font-medium mt-1">{counts[band.id] || 0}</p>
              <p className="text-xs text-[var(--muted)] mt-1">instruments</p>
            </Link>
          ))}
        </div>
      </section>

      <section>
        <div className="flex items-end justify-between gap-4 mb-4">
          <h2 className="text-xl font-medium">High-severity flags</h2>
          <Link
            href={withProfile("/issues", profile)}
            className="text-sm text-[var(--muted)] hover:text-[var(--fg)]"
          >
            All →
          </Link>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {highs.map((issue) => (
            <NodeCard key={issue.id} node={issue} />
          ))}
        </div>
      </section>
    </div>
  );
}
