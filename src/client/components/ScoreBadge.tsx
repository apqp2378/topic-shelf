import clsx from 'clsx';

type ScoreBadgeProps = {
  score: number;
};

const getToneClassName = (score: number): string => {
  if (score >= 10) {
    return 'border-emerald-300 bg-emerald-100 text-emerald-800';
  }

  if (score >= 7) {
    return 'border-amber-300 bg-amber-100 text-amber-800';
  }

  return 'border-slate-300 bg-slate-100 text-slate-700';
};

export const ScoreBadge = ({ score }: ScoreBadgeProps) => (
  <span
    className={clsx(
      'inline-flex items-center rounded-md border px-2 py-1 text-xs font-semibold',
      getToneClassName(score)
    )}
  >
    Score {score}
  </span>
);
