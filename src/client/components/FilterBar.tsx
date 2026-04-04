import {
  candidateSorts,
  candidateStatuses,
  isCandidateSort,
  isCandidateStatus,
  type CandidateSort,
  type CandidateStatusFilter,
} from '../../shared/candidate';

type FilterBarProps = {
  status: CandidateStatusFilter;
  sort: CandidateSort;
  disabled?: boolean;
  onStatusChange: (status: CandidateStatusFilter) => void;
  onSortChange: (sort: CandidateSort) => void;
  onRefresh: () => void;
  onOpenExport: () => void;
};

export const FilterBar = ({
  status,
  sort,
  disabled,
  onStatusChange,
  onSortChange,
  onRefresh,
  onOpenExport,
}: FilterBarProps) => (
  <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
    <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div className="flex flex-col gap-4 sm:flex-row">
        <label className="flex flex-col gap-1 text-sm text-slate-600">
          <span className="font-medium">Status</span>
          <select
            value={status}
            disabled={disabled}
            onChange={(event) => {
              const nextValue = event.target.value;
              if (nextValue === 'all' || isCandidateStatus(nextValue)) {
                onStatusChange(nextValue);
              }
            }}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
          >
            <option value="all">all</option>
            {candidateStatuses.map((candidateStatus) => (
              <option key={candidateStatus} value={candidateStatus}>
                {candidateStatus}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm text-slate-600">
          <span className="font-medium">Sort</span>
          <select
            value={sort}
            disabled={disabled}
            onChange={(event) => {
              const nextValue = event.target.value;
              if (isCandidateSort(nextValue)) {
                onSortChange(nextValue);
              }
            }}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
          >
            {candidateSorts.map((candidateSort) => (
              <option key={candidateSort} value={candidateSort}>
                {candidateSort}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={disabled}
          onClick={onRefresh}
          className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white"
        >
          Refresh candidates
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={onOpenExport}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700"
        >
          Open export
        </button>
      </div>
    </div>
  </div>
);
