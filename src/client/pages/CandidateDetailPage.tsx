import { navigateTo } from '@devvit/web/client';
import { getRecommendedStatus } from '../../shared/candidate';
import { ScoreBadge } from '../components/ScoreBadge';
import { StatusButtons } from '../components/StatusButtons';
import { TopCommentList } from '../components/TopCommentList';
import type { Candidate, CandidateStatus } from '../types/candidate';

type CandidateDetailPageProps = {
  candidate: Candidate;
  noteDraft: string;
  saving: boolean;
  onBack: () => void;
  onStatusChange: (status: CandidateStatus) => void;
  onNoteDraftChange: (value: string) => void;
  onSaveNote: () => void;
};

export const CandidateDetailPage = ({
  candidate,
  noteDraft,
  saving,
  onBack,
  onStatusChange,
  onNoteDraftChange,
  onSaveNote,
}: CandidateDetailPageProps) => (
  <div className="space-y-4">
    <div className="flex items-center justify-between gap-3">
      <button
        type="button"
        onClick={onBack}
        className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700"
      >
        Back to list
      </button>
      <button
        type="button"
        onClick={() => navigateTo(candidate.permalink)}
        className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white"
      >
        Open Reddit post
      </button>
    </div>

    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            Candidate detail
          </p>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">{candidate.title}</h1>
          <p className="mt-2 text-sm text-slate-500">
            u/{candidate.author} • r/{candidate.subreddit}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <ScoreBadge score={candidate.score} />
          <span className="rounded-md border border-sky-200 bg-sky-50 px-2 py-1 text-xs font-semibold text-sky-800">
            Recommended: {getRecommendedStatus(candidate.score)}
          </span>
        </div>
      </div>

      <div className="mt-4 grid gap-3 text-sm text-slate-600 sm:grid-cols-3">
        <div className="rounded-lg bg-slate-50 p-3">
          <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Created</p>
          <p className="mt-1 font-medium text-slate-900">
            {new Date(candidate.created_utc * 1000).toLocaleString()}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Upvotes</p>
          <p className="mt-1 font-medium text-slate-900">{candidate.upvotes}</p>
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Comments</p>
          <p className="mt-1 font-medium text-slate-900">{candidate.num_comments}</p>
        </div>
      </div>

      <div className="mt-4">
        <h2 className="text-sm font-semibold text-slate-900">Body excerpt</h2>
        <p className="mt-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm leading-6 text-slate-700">
          {candidate.body_excerpt || 'No body excerpt was available.'}
        </p>
      </div>

      <div className="mt-4">
        <h2 className="text-sm font-semibold text-slate-900">Reason tags</h2>
        <div className="mt-2 flex flex-wrap gap-2">
          {candidate.reason_tags.map((tag) => (
            <span key={tag} className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-700">
              {tag}
            </span>
          ))}
        </div>
      </div>
    </section>

    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-900">Moderator status</h2>
      <div className="mt-3">
        <StatusButtons
          currentStatus={candidate.status}
          disabled={saving}
          onChange={onStatusChange}
        />
      </div>

      <div className="mt-5">
        <label className="block text-sm font-semibold text-slate-900" htmlFor="review-note">
          Review note
        </label>
        <textarea
          id="review-note"
          value={noteDraft}
          disabled={saving}
          onChange={(event) => onNoteDraftChange(event.target.value)}
          rows={5}
          className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900"
          placeholder="Save moderator notes for later review."
        />
        <button
          type="button"
          disabled={saving}
          onClick={onSaveNote}
          className="mt-3 rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white"
        >
          Save note
        </button>
      </div>
    </section>

    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-900">Top comments</h2>
      <div className="mt-3">
        <TopCommentList comments={candidate.top_comments} />
      </div>
    </section>
  </div>
);
