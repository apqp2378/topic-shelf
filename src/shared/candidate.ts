export type CandidateStatus = 'new' | 'keep' | 'review' | 'drop';

export type CandidateSort = 'score' | 'latest' | 'comments';

export type CandidateStatusFilter = CandidateStatus | 'all';

export type TopComment = {
  comment_id: string;
  author: string;
  body: string;
  body_excerpt: string;
  score: number;
  created_utc: number;
};

export type Candidate = {
  candidate_id: string;
  post_id: string;
  permalink: string;
  title: string;
  author: string;
  subreddit: string;
  created_utc: number;
  upvotes: number;
  num_comments: number;
  post_body: string;
  body_excerpt: string;
  top_comments: TopComment[];
  score: number;
  reason_tags: string[];
  status: CandidateStatus;
  review_note: string;
};

export type CandidateScoreResult = {
  score: number;
  reason_tags: string[];
};

export type CandidateListResponse = {
  candidates: Candidate[];
  count: number;
  status: CandidateStatusFilter;
  sort: CandidateSort;
  subreddit: string;
  refreshed_at: number | null;
};

export type CandidateDetailResponse = {
  candidate: Candidate;
};

export type CandidateMutationResponse = {
  candidate: Candidate;
};

export type KeepExportResponse = {
  count: number;
  content: string;
  refreshed_at: number | null;
};

export type KeepRawJsonTopComment = {
  comment_id: string;
  author: string;
  body: string;
  score: number;
  created_utc: number;
};

export type KeepRawJsonCandidate = {
  raw_id: string;
  source: 'reddit_devvit';
  subreddit: string;
  post_title: string;
  post_url: string;
  post_author: string;
  post_created_utc: number;
  post_body: string;
  num_comments: number;
  upvotes: number;
  top_comments: KeepRawJsonTopComment[];
  devvit_score: number;
  devvit_reason_tags: string[];
  moderator_status: CandidateStatus;
  review_note: string;
  collected_at: string;
  recommended_status: CandidateStatus;
  candidate_rank: number;
  post_id: string;
  candidate_id: string;
  body_excerpt: string;
  devvit_version: 'v1.1';
};

export type RefreshCandidatesResponse = {
  ok: boolean;
  refreshed_at: number;
  subreddit: string;
  processed_count: number;
};

export const candidateStatuses: CandidateStatus[] = [
  'new',
  'keep',
  'review',
  'drop',
];

export const candidateSorts: CandidateSort[] = ['score', 'latest', 'comments'];

export const isCandidateStatus = (value: string): value is CandidateStatus =>
  candidateStatuses.some((status) => status === value);

export const isCandidateSort = (value: string): value is CandidateSort =>
  candidateSorts.some((sort) => sort === value);

export const getRecommendedStatus = (score: number): CandidateStatus => {
  if (score >= 10) {
    return 'keep';
  }

  if (score >= 7) {
    return 'review';
  }

  return 'drop';
};
