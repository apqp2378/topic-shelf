export type CandidateStatus = 'new' | 'keep' | 'review' | 'drop';

export type CandidateSort = 'score' | 'latest' | 'comments';

export type CandidateStatusFilter = CandidateStatus | 'all';

export type TopComment = {
  comment_id: string;
  body_excerpt: string;
  score: number;
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
