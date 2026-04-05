import clsx from 'clsx';
import type { CandidateStatus } from '../types/candidate';

type StatusBadgeKind = 'recommended' | 'moderator';

type StatusBadgeProps = {
  label: string;
  status: CandidateStatus;
  kind: StatusBadgeKind;
};

const getToneClasses = (kind: StatusBadgeKind, status: CandidateStatus): string => {
  if (kind === 'recommended') {
    return 'border-sky-200 bg-sky-50 text-sky-800';
  }

  if (status === 'keep') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-800';
  }

  if (status === 'review') {
    return 'border-amber-200 bg-amber-50 text-amber-800';
  }

  if (status === 'drop') {
    return 'border-rose-200 bg-rose-50 text-rose-800';
  }

  return 'border-slate-200 bg-slate-50 text-slate-700';
};

export const StatusBadge = ({ label, status, kind }: StatusBadgeProps) => (
  <span
    className={clsx(
      'inline-flex items-center rounded-md border px-2 py-1 text-xs font-semibold',
      getToneClasses(kind, status)
    )}
  >
    {label}: {status}
  </span>
);
