import clsx from 'clsx';
import {
  candidateStatuses,
  type CandidateStatus,
} from '../../shared/candidate';

type StatusButtonsProps = {
  currentStatus: CandidateStatus;
  disabled: boolean | undefined;
  onChange: (status: CandidateStatus) => void;
};

const statusTone = (status: CandidateStatus, isActive: boolean): string => {
  if (!isActive) {
    return 'border-slate-300 bg-white text-slate-700 hover:border-slate-400';
  }

  if (status === 'keep') {
    return 'border-emerald-500 bg-emerald-600 text-white';
  }

  if (status === 'review') {
    return 'border-amber-500 bg-amber-500 text-white';
  }

  if (status === 'drop') {
    return 'border-rose-500 bg-rose-600 text-white';
  }

  return 'border-sky-500 bg-sky-600 text-white';
};

export const StatusButtons = ({
  currentStatus,
  disabled,
  onChange,
}: StatusButtonsProps) => (
  <div className="flex flex-wrap gap-2">
    {candidateStatuses.map((status) => {
      const isActive = status === currentStatus;

      return (
        <button
          key={status}
          type="button"
          disabled={disabled}
          onClick={() => onChange(status)}
          className={clsx(
            'rounded-md border px-3 py-1.5 text-xs font-semibold capitalize transition',
            disabled ? 'cursor-not-allowed opacity-60' : '',
            statusTone(status, isActive)
          )}
        >
          {status}
        </button>
      );
    })}
  </div>
);
