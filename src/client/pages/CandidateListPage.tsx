import { CandidateCard } from '../components/CandidateCard';
import { FilterBar } from '../components/FilterBar';
import type {
  Candidate,
  CandidateSort,
  CandidateStatus,
  CandidateStatusFilter,
} from '../types/candidate';

type CandidateListPageProps = {
  candidates: Candidate[];
  count: number;
  sort: CandidateSort;
  status: CandidateStatusFilter;
  loading: boolean;
  refreshedAt: number | null;
  subreddit: string;
  onStatusChange: (status: CandidateStatusFilter) => void;
  onSortChange: (sort: CandidateSort) => void;
  onRefresh: () => void;
  onOpenExport: () => void;
  onOpenDetail: (candidateId: string) => void;
  onCandidateStatusChange: (candidateId: string, status: CandidateStatus) => void;
};

const formatRefreshTime = (value: number | null): string => {
  if (!value) {
    return 'No refresh has run yet.';
  }

  return new Date(value).toLocaleString();
};

export const CandidateListPage = ({
  candidates,
  count,
  sort,
  status,
  loading,
  refreshedAt,
  subreddit,
  onStatusChange,
  onSortChange,
  onRefresh,
  onOpenExport,
  onOpenDetail,
  onCandidateStatusChange,
}: CandidateListPageProps) => (
  <div className="space-y-4">
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
        Moderator Dashboard
      </p>
      <h1 className="mt-2 text-2xl font-bold text-slate-900">Reddit candidate picker</h1>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        Reviewing r/{subreddit} candidates with human-owned statuses and notes.
      </p>
      <p className="mt-3 text-xs text-slate-500">
        {count} candidates · Last refresh: {formatRefreshTime(refreshedAt)}
      </p>
    </section>

    <FilterBar
      status={status}
      sort={sort}
      disabled={loading}
      onStatusChange={onStatusChange}
      onSortChange={onSortChange}
      onRefresh={onRefresh}
      onOpenExport={onOpenExport}
    />

    <section className="space-y-3">
      {candidates.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-500">
          No candidates match the current filter yet.
        </div>
      ) : (
        candidates.map((candidate) => (
          <CandidateCard
            key={candidate.candidate_id}
            candidate={candidate}
            disabled={loading}
            onOpen={onOpenDetail}
            onStatusChange={onCandidateStatusChange}
          />
        ))
      )}
    </section>
  </div>
);
