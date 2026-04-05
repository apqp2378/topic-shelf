import type { Candidate, CandidateScoreResult, TopComment } from '../../shared/candidate';
import type { RedditPostRecord } from './redditService';

const normalizeExcerpt = (value: string, maxLength: number): string =>
  value.replace(/\s+/g, ' ').trim().slice(0, maxLength);

export const mapToCandidate = (
  post: RedditPostRecord,
  topComments: TopComment[],
  scoreResult: CandidateScoreResult
): Candidate => ({
  candidate_id: post.post_id,
  post_id: post.post_id,
  permalink: post.permalink.startsWith('http')
    ? post.permalink
    : `https://reddit.com${post.permalink}`,
  title: post.title,
  author: post.author,
  subreddit: post.subreddit,
  created_utc: post.created_utc,
  upvotes: post.upvotes,
  num_comments: post.num_comments,
  post_body: post.body,
  body_excerpt: normalizeExcerpt(post.body, 300),
  top_comments: topComments,
  score: scoreResult.score,
  reason_tags: [...new Set(scoreResult.reason_tags)],
  status: 'new',
  review_note: '',
});
