import type { TopComment } from '../types/candidate';

type TopCommentListProps = {
  comments: TopComment[];
};

export const TopCommentList = ({ comments }: TopCommentListProps) => {
  if (comments.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-3 text-sm text-slate-500">
        No top comments were captured for this post.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {comments.map((comment, index) => (
        <article
          key={comment.comment_id}
          className="rounded-lg border border-slate-200 bg-white p-3"
        >
          <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
            <span>Top comment #{index + 1}</span>
            <span>{comment.score} score</span>
          </div>
          <p className="text-sm leading-6 text-slate-700">{comment.body_excerpt}</p>
        </article>
      ))}
    </div>
  );
};
