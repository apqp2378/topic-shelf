import type { RefreshCandidatesResponse } from '../../shared/candidate';
import { mapToCandidate } from '../services/candidateMapper';
import { scoreCandidate } from '../services/candidateScorer';
import {
  getCandidateByPostId,
  setLastRefreshMeta,
  removeExcludedCandidates,
  upsertCandidate,
} from '../services/candidateStore';
import {
  fetchRecentPosts,
  fetchTopComments,
  resolveTargetSubreddit,
} from '../services/redditService';

export const refreshCandidatesJob = async (): Promise<RefreshCandidatesResponse> => {
  const subreddit = await resolveTargetSubreddit();
  const posts = await fetchRecentPosts(subreddit);

  await Promise.all(
    posts.map(async (post) => {
      const topComments = await fetchTopComments(post.post_id);
      const scoreResult = scoreCandidate({
        createdUtc: post.created_utc,
        title: post.title,
        body: post.body,
        numComments: post.num_comments,
        topComments,
      });

      const nextCandidate = mapToCandidate(post, topComments, scoreResult);
      const existingCandidate = await getCandidateByPostId(post.post_id);

      await upsertCandidate({
        ...nextCandidate,
        status: existingCandidate?.status ?? 'new',
        review_note: existingCandidate?.review_note ?? '',
      });
    })
  );

  await removeExcludedCandidates();

  const refreshedAt = Date.now();
  await setLastRefreshMeta(refreshedAt, subreddit);

  return {
    ok: true,
    refreshed_at: refreshedAt,
    subreddit,
    processed_count: posts.length,
  };
};

export const refreshCandidates = refreshCandidatesJob;
