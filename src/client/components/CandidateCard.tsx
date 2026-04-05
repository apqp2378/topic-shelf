import { navigateTo } from '@devvit/web/client';
import { getRecommendedStatus } from '../../shared/candidate';
import { ScoreBadge } from './ScoreBadge';
import { StatusBadge } from './StatusBadge';
import { StatusButtons } from './StatusButtons';
import type { Candidate, CandidateStatus } from '../types/candidate';

type CandidateCardProps = {
  candidate: Candidate;
  disabled?: boolean;
  onOpen: (candidateId: string) => void;
  onStatusChange: (candidateId: string, status: CandidateStatus) => void;
};

export const CandidateCard = ({
  candidate,
  disabled,
  onOpen,
  onStatusChange,
}: CandidateCardProps) => (
  <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
    <div className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <button
            type="button"
            onClick={() => onOpen(candidate.candidate_id)}
            className="text-left text-base font-semibold text-slate-900 underline-offset-4 hover:underline"
          >
            {candidate.title}
          </button>
          <p className="mt-1 text-xs text-slate-500">
            u/{candidate.author} · {candidate.num_comments} comments · {candidate.upvotes} upvotes
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <ScoreBadge score={candidate.score} />
          <StatusBadge
            label="Recommended"
            status={getRecommendedStatus(candidate.score)}
            kind="recommended"
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <StatusBadge label="Moderator status" status={candidate.status} kind="moderator" />
      </div>

      <p className="text-sm leading-6 text-slate-700">
        {candidate.body_excerpt || 'No post body excerpt.'}
      </p>

      <div className="flex flex-wrap gap-2 text-xs text-slate-500">
        {candidate.reason_tags.map((tag) => (
          <span key={tag} className="rounded-md bg-slate-100 px-2 py-1">
            {tag}
          </span>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <StatusButtons
          currentStatus={candidate.status}
          disabled={disabled}
          onChange={(status) => onStatusChange(candidate.candidate_id, status)}
        />
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onOpen(candidate.candidate_id)}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700"
          >
            Open detail
          </button>
          <button
            type="button"
            onClick={() => navigateTo(candidate.permalink)}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700"
          >
            Open post
          </button>
        </div>
      </div>
    </div>
  </article>
);
