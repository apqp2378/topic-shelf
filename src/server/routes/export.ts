import { Hono } from 'hono';
import type { KeepExportResponse } from '../../shared/candidate';
import { getKeepCandidates } from '../services/candidateStore';

const buildPlainTextExport = (links: string[]): string => links.join('\n');

const buildMarkdownExport = (links: string[]): string =>
  links.map((link) => `- ${link}`).join('\n');

export const exportRoute = new Hono();

exportRoute.get('/keep-links', async (c) => {
  try {
    const candidates = await getKeepCandidates();
    const links = candidates.map((candidate) => candidate.permalink);

    return c.json<KeepExportResponse>({
      count: links.length,
      content: buildPlainTextExport(links),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to export links';
    return c.json({ message }, 500);
  }
});

exportRoute.get('/keep-markdown', async (c) => {
  try {
    const candidates = await getKeepCandidates();
    const links = candidates.map((candidate) => candidate.permalink);

    return c.json<KeepExportResponse>({
      count: links.length,
      content: buildMarkdownExport(links),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to export markdown';
    return c.json({ message }, 500);
  }
});
