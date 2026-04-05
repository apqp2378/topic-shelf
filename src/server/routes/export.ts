import { Hono } from 'hono';
import type {
  KeepExportResponse,
  KeepRawJsonCandidate,
} from '../../shared/candidate';
import { getLastRefreshMeta, getKeepCandidates } from '../services/candidateStore';
import { mapKeepCandidateToRawExport } from '../services/rawExportMapper';

const buildPlainTextExport = (
  candidates: { title: string; permalink: string }[]
): string =>
  candidates
    .map((candidate) => `${candidate.title}\n${candidate.permalink}`)
    .join('\n\n');

const buildMarkdownExport = (
  candidates: { title: string; permalink: string }[]
): string =>
  candidates
    .map((candidate) => `- ${candidate.title}\n  - ${candidate.permalink}`)
    .join('\n\n');

const formatExportDate = (value: Date): string => value.toISOString().slice(0, 10);

export const exportRoute = new Hono();

exportRoute.get('/keep-links', async (c) => {
  try {
    const [candidates, refreshMeta] = await Promise.all([
      getKeepCandidates(),
      getLastRefreshMeta(),
    ]);

    return c.json<KeepExportResponse>({
      count: candidates.length,
      content: buildPlainTextExport(candidates),
      refreshed_at: refreshMeta.refreshed_at,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to export links';
    return c.json({ message }, 500);
  }
});

exportRoute.get('/keep-markdown', async (c) => {
  try {
    const [candidates, refreshMeta] = await Promise.all([
      getKeepCandidates(),
      getLastRefreshMeta(),
    ]);

    return c.json<KeepExportResponse>({
      count: candidates.length,
      content: buildMarkdownExport(candidates),
      refreshed_at: refreshMeta.refreshed_at,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to export markdown';
    return c.json({ message }, 500);
  }
});

exportRoute.get('/keep-raw-json', async (c) => {
  try {
    const candidates = await getKeepCandidates();
    const collectedAt = new Date().toISOString();
    const exportDate = formatExportDate(new Date(collectedAt));
    const payload: KeepRawJsonCandidate[] = candidates.map((candidate, index) =>
      mapKeepCandidateToRawExport(candidate, index, collectedAt, exportDate)
    );

    return c.json<KeepRawJsonCandidate[]>(payload, 200);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : 'Failed to export raw JSON';
    return c.json({ message }, 500);
  }
});
