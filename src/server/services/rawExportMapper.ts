import {
  getRecommendedStatus,
  type Candidate,
  type KeepRawJsonCandidate,
} from '../../shared/candidate';

const buildRawId = (exportDate: string, index: number): string =>
  `reddit_devvit_${exportDate}_${String(index + 1).padStart(3, '0')}`;

export const mapKeepCandidateToRawExport = (
  candidate: Candidate,
  index: number,
  collectedAt: string,
  exportDate: string
): KeepRawJsonCandidate => ({
  raw_id: buildRawId(exportDate, index),
  source: 'reddit_devvit',
  subreddit: candidate.subreddit,
  post_title: candidate.title,
  post_url: candidate.permalink,
  post_author: candidate.author,
  post_created_utc: candidate.created_utc,
  post_body: candidate.post_body || candidate.body_excerpt,
  num_comments: candidate.num_comments,
  upvotes: candidate.upvotes,
  top_comments: candidate.top_comments.map((comment) => ({
    comment_id: comment.comment_id,
    author: comment.author,
    body: comment.body || comment.body_excerpt,
    score: comment.score,
    created_utc: comment.created_utc,
  })),
  devvit_score: candidate.score,
  devvit_reason_tags: [...candidate.reason_tags],
  moderator_status: candidate.status,
  review_note: candidate.review_note,
  collected_at: collectedAt,
  recommended_status: getRecommendedStatus(candidate.score),
  candidate_rank: index + 1,
  post_id: candidate.post_id,
  candidate_id: candidate.candidate_id,
  body_excerpt: candidate.body_excerpt,
  devvit_version: 'v1.1',
});
