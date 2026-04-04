import { Hono } from 'hono';
import {
  isCandidateSort,
  isCandidateStatus,
  type CandidateDetailResponse,
  type CandidateListResponse,
} from '../../shared/candidate';
import { resolveTargetSubreddit } from '../services/redditService';
import {
  getCandidateById,
  getLastRefreshMeta,
  listCandidates,
} from '../services/candidateStore';
import { refreshCandidatesJob } from '../scheduler/refreshCandidates';

export const candidatesRoute = new Hono();

candidatesRoute.get('/', async (c) => {
  try {
    const sortValue = c.req.query('sort') ?? 'score';
    const statusValue = c.req.query('status') ?? 'all';
    const sort = isCandidateSort(sortValue) ? sortValue : 'score';
    const status =
      statusValue === 'all' || isCandidateStatus(statusValue) ? statusValue : 'all';
    const [candidates, refreshMeta, subreddit] = await Promise.all([
      listCandidates(sort, status),
      getLastRefreshMeta(),
      resolveTargetSubreddit(),
    ]);

    return c.json<CandidateListResponse>({
      candidates,
      count: candidates.length,
      sort,
      status,
      subreddit: refreshMeta.subreddit || subreddit,
      refreshed_at: refreshMeta.refreshed_at,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to load candidates';
    return c.json({ message }, 500);
  }
});

candidatesRoute.get('/:id', async (c) => {
  try {
    const candidateId = c.req.param('id');
    const candidate = await getCandidateById(candidateId);

    if (!candidate) {
      return c.json({ message: 'Candidate not found' }, 404);
    }

    return c.json<CandidateDetailResponse>({
      candidate,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to load candidate';
    return c.json({ message }, 500);
  }
});

candidatesRoute.post('/refresh', async (c) => {
  try {
    const result = await refreshCandidatesJob();
    return c.json(result, 200);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : 'Failed to refresh candidates';
    return c.json({ message }, 500);
  }
});
