import { Hono } from 'hono';
import {
  isCandidateStatus,
  type CandidateMutationResponse,
} from '../../shared/candidate';
import {
  updateCandidateReviewNote,
  updateCandidateStatus,
} from '../services/candidateStore';

type StatusRequest = {
  status?: string;
};

type NoteRequest = {
  review_note?: string;
};

export const actionsRoute = new Hono();

actionsRoute.post('/:id/status', async (c) => {
  try {
    const candidateId = c.req.param('id');
    const body = await c.req.json<StatusRequest>();
    const statusValue = body.status ?? '';

    if (!isCandidateStatus(statusValue)) {
      return c.json({ message: 'Invalid status value' }, 400);
    }

    const candidate = await updateCandidateStatus(candidateId, statusValue);
    if (!candidate) {
      return c.json({ message: 'Candidate not found' }, 404);
    }

    return c.json<CandidateMutationResponse>({
      candidate,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to update status';
    return c.json({ message }, 500);
  }
});

actionsRoute.post('/:id/note', async (c) => {
  try {
    const candidateId = c.req.param('id');
    const body = await c.req.json<NoteRequest>();
    const reviewNote = (body.review_note ?? '').trim();
    const candidate = await updateCandidateReviewNote(candidateId, reviewNote);

    if (!candidate) {
      return c.json({ message: 'Candidate not found' }, 404);
    }

    return c.json<CandidateMutationResponse>({
      candidate,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to update note';
    return c.json({ message }, 500);
  }
});
