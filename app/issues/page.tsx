import { IssueList } from "@/components/issue-list";
import { parseProfile } from "@/lib/catalog";
import { flaggedTargets, issuesForProfile } from "@/lib/data";

export default async function IssuesPage({
  searchParams,
}: {
  searchParams: Promise<{ profile?: string }>;
}) {
  const params = await searchParams;
  const profile = parseProfile(params.profile);
  const issues = issuesForProfile(profile);
  const related = Object.fromEntries(
    issues.map((issue) => [issue.id, flaggedTargets(issue.id, profile)]),
  );

  return <IssueList issues={issues} related={related} />;
}
