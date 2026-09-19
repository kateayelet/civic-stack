import { CorpusList } from "@/components/corpus-list";
import { BANDS, corpusNote, parseProfile } from "@/lib/catalog";
import { lawsForProfile } from "@/lib/data";

export default async function CorpusPage({
  searchParams,
}: {
  searchParams: Promise<{ profile?: string; band?: string }>;
}) {
  const params = await searchParams;
  const profile = parseProfile(params.profile);
  const band =
    BANDS.some((item) => item.id === params.band) && params.band
      ? params.band
      : "all";
  const nodes = lawsForProfile(profile);

  return (
    <CorpusList
      profile={profile}
      band={band}
      nodes={nodes}
      note={corpusNote(profile)}
    />
  );
}
