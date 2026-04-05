import { redis } from '@devvit/web/server';
import {
  isCandidateSort,
  isCandidateStatus,
  type Candidate,
  type CandidateSort,
  type CandidateStatus,
  type CandidateStatusFilter,
} from '../../shared/candidate';
import {
  getExcludedCandidateReason,
  isDashboardPostTitle,
} from '../config/exclusion';

const CANDIDATE_HASH_KEY = 'candidate-picker:candidates';
const REFRESH_META_KEY = 'candidate-picker:meta';

export const isExcludedCandidateTitle = (title: string): boolean => {
  return isDashboardPostTitle(title);
};

export const isExcludedCandidate = (candidate: Pick<Candidate, 'title' | 'author'>): boolean =>
  getExcludedCandidateReason(candidate) !== null;

const parseTopComments = (value: unknown): Candidate['top_comments'] => {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter(
      (comment) =>
        typeof comment === 'object' &&
        comment !== null &&
        typeof comment.comment_id === 'string' &&
        typeof comment.score === 'number'
    )
    .map((comment) => {
      const commentId = Reflect.get(comment, 'comment_id');
      const author = Reflect.get(comment, 'author');
      const body = Reflect.get(comment, 'body');
      const bodyExcerpt = Reflect.get(comment, 'body_excerpt');
      const score = Reflect.get(comment, 'score');
      const createdUtc = Reflect.get(comment, 'created_utc');
      const normalizedBody =
        typeof body === 'string'
          ? body
          : typeof bodyExcerpt === 'string'
            ? bodyExcerpt
            : '';

      return {
        comment_id: typeof commentId === 'string' ? commentId : '',
        author: typeof author === 'string' ? author : '[unknown]',
        body: normalizedBody,
        body_excerpt: typeof bodyExcerpt === 'string' ? bodyExcerpt : '',
        score: typeof score === 'number' ? score : 0,
        created_utc: typeof createdUtc === 'number' ? createdUtc : 0,
      };
    });
};

const parseCandidate = (raw: string | undefined): Candidate | null => {
  if (!raw) {
    return null;
  }

  try {
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== 'object' || parsed === null) {
      return null;
    }

    const candidateIdValue = Reflect.get(parsed, 'candidate_id');
    const statusFieldValue = Reflect.get(parsed, 'status');
    const candidateId = typeof candidateIdValue === 'string' ? candidateIdValue : '';
    const statusValue =
      typeof statusFieldValue === 'string' ? statusFieldValue : '';
    if (!candidateId || !isCandidateStatus(statusValue)) {
      return null;
    }

    const postIdValue = Reflect.get(parsed, 'post_id');
    const permalinkValue = Reflect.get(parsed, 'permalink');
    const titleValue = Reflect.get(parsed, 'title');
    const authorValue = Reflect.get(parsed, 'author');
    const subredditValue = Reflect.get(parsed, 'subreddit');
    const createdUtcValue = Reflect.get(parsed, 'created_utc');
    const upvotesValue = Reflect.get(parsed, 'upvotes');
    const numCommentsValue = Reflect.get(parsed, 'num_comments');
    const bodyExcerptValue = Reflect.get(parsed, 'body_excerpt');
    const postBodyValue = Reflect.get(parsed, 'post_body');
    const topCommentsValue = Reflect.get(parsed, 'top_comments');
    const scoreValue = Reflect.get(parsed, 'score');
    const reasonTagsValue = Reflect.get(parsed, 'reason_tags');
    const reviewNoteValue = Reflect.get(parsed, 'review_note');

    return {
      candidate_id: candidateId,
      post_id: typeof postIdValue === 'string' ? postIdValue : candidateId,
      permalink: typeof permalinkValue === 'string' ? permalinkValue : '',
      title: typeof titleValue === 'string' ? titleValue : '',
      author: typeof authorValue === 'string' ? authorValue : '[unknown]',
      subreddit: typeof subredditValue === 'string' ? subredditValue : '',
      created_utc: typeof createdUtcValue === 'number' ? createdUtcValue : 0,
      upvotes: typeof upvotesValue === 'number' ? upvotesValue : 0,
      num_comments:
        typeof numCommentsValue === 'number' ? numCommentsValue : 0,
      post_body:
        typeof postBodyValue === 'string'
          ? postBodyValue
          : typeof bodyExcerptValue === 'string'
            ? bodyExcerptValue
            : '',
      body_excerpt:
        typeof bodyExcerptValue === 'string' ? bodyExcerptValue : '',
      top_comments: parseTopComments(topCommentsValue),
      score: typeof scoreValue === 'number' ? scoreValue : 0,
      reason_tags: Array.isArray(reasonTagsValue)
        ? reasonTagsValue.filter((tag): tag is string => typeof tag === 'string')
        : [],
      status: statusValue,
      review_note: typeof reviewNoteValue === 'string' ? reviewNoteValue : '',
    };
  } catch {
    return null;
  }
};

const sortCandidates = (
  candidates: Candidate[],
  sort: CandidateSort
): Candidate[] => {
  const sorted = [...candidates];

  if (sort === 'latest') {
    sorted.sort((left, right) => right.created_utc - left.created_utc);
    return sorted;
  }

  if (sort === 'comments') {
    sorted.sort((left, right) => right.num_comments - left.num_comments);
    return sorted;
  }

  sorted.sort((left, right) => right.score - left.score);
  return sorted;
};

export const upsertCandidate = async (candidate: Candidate): Promise<Candidate> => {
  await redis.hSet(CANDIDATE_HASH_KEY, {
    [candidate.candidate_id]: JSON.stringify(candidate),
  });
  return candidate;
};

export const getCandidateById = async (
  candidateId: string
): Promise<Candidate | null> => {
  const candidate = parseCandidate(await redis.hGet(CANDIDATE_HASH_KEY, candidateId));
  if (!candidate || isExcludedCandidate(candidate)) {
    return null;
  }

  return candidate;
};

export const getCandidateByPostId = async (
  postId: string
): Promise<Candidate | null> => getCandidateById(postId);

export const listAllCandidates = async (): Promise<Candidate[]> => {
  const rows = await redis.hGetAll(CANDIDATE_HASH_KEY);
  return Object.values(rows)
    .map((raw) => parseCandidate(raw))
    .filter(
      (candidate): candidate is Candidate =>
        candidate !== null && !isExcludedCandidate(candidate)
    );
};

export const listCandidates = async (
  sort: string,
  status: string
): Promise<Candidate[]> => {
  const normalizedSort: CandidateSort = isCandidateSort(sort) ? sort : 'score';
  const normalizedStatus: CandidateStatusFilter =
    status === 'all' || isCandidateStatus(status) ? status : 'all';

  const allCandidates = await listAllCandidates();
  const filteredCandidates =
    normalizedStatus === 'all'
      ? allCandidates
      : allCandidates.filter((candidate) => candidate.status === normalizedStatus);

  return sortCandidates(filteredCandidates, normalizedSort);
};

export const updateCandidateStatus = async (
  candidateId: string,
  status: CandidateStatus
): Promise<Candidate | null> => {
  const candidate = await getCandidateById(candidateId);
  if (!candidate) {
    return null;
  }

  const updated = {
    ...candidate,
    status,
  };
  await upsertCandidate(updated);
  return updated;
};

export const updateCandidateReviewNote = async (
  candidateId: string,
  reviewNote: string
): Promise<Candidate | null> => {
  const candidate = await getCandidateById(candidateId);
  if (!candidate) {
    return null;
  }

  const updated = {
    ...candidate,
    review_note: reviewNote,
  };
  await upsertCandidate(updated);
  return updated;
};

export const getKeepCandidates = async (): Promise<Candidate[]> => {
  const candidates = await listAllCandidates();
  return sortCandidates(
    candidates.filter((candidate) => candidate.status === 'keep'),
    'score'
  );
};

export const removeExcludedCandidates = async (): Promise<number> => {
  const rows = await redis.hGetAll(CANDIDATE_HASH_KEY);
  const excludedIds = Object.entries(rows)
    .map(([candidateId, raw]) => {
      const candidate = parseCandidate(raw);
      if (!candidate || !isExcludedCandidate(candidate)) {
        return null;
      }

      const reason = getExcludedCandidateReason(candidate);
      console.debug(
        'Removing excluded candidate from storage:',
        candidateId,
        reason,
        candidate.title
      );
      return candidateId;
    })
    .filter((candidateId): candidateId is string => candidateId !== null);

  if (excludedIds.length === 0) {
    return 0;
  }

  await redis.del(...excludedIds);
  return excludedIds.length;
};

export const setLastRefreshMeta = async (
  refreshedAt: number,
  subreddit: string
): Promise<void> => {
  await redis.hSet(REFRESH_META_KEY, {
    refreshed_at: `${refreshedAt}`,
    subreddit,
  });
};

export const getLastRefreshMeta = async (): Promise<{
  refreshed_at: number | null;
  subreddit: string;
}> => {
  const values = await redis.hGetAll(REFRESH_META_KEY);
  const refreshedAtValue = values.refreshed_at;
  const refreshedAtNumber = refreshedAtValue ? Number(refreshedAtValue) : NaN;

  return {
    refreshed_at: Number.isFinite(refreshedAtNumber) ? refreshedAtNumber : null,
    subreddit: values.subreddit ?? '',
  };
};
