import { Hono } from 'hono';
import { serve } from '@hono/node-server';
import { createServer, getServerPort, context, reddit } from '@devvit/web/server';
import { candidatesRoute } from './routes/candidates';
import { actionsRoute } from './routes/actions';
import { exportRoute } from './routes/export';
import { refreshCandidatesJob } from './scheduler/refreshCandidates';

const app = new Hono();
const internal = new Hono();
const api = new Hono();

api.route('/candidates', candidatesRoute);
api.route('/candidates', actionsRoute);
api.route('/export', exportRoute);

internal.post('/scheduler/refresh-candidates', async (c) => {
  try {
    const result = await refreshCandidatesJob();
    return c.json(result, 200);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : 'Failed to refresh candidates';
    return c.json({ message }, 500);
  }
});

internal.post('/menu/create-dashboard-post', async (c) => {
  try {
    const post = await reddit.submitCustomPost({
      subredditName: context.subredditName,
      title: 'Candidate Picker Dashboard',
      entry: 'game',
      textFallback: {
        text: 'Open this Devvit dashboard post to review, score, and export subreddit candidates.',
      },
    });

    return c.json(
      {
        ok: true,
        postId: post.id,
        permalink: post.permalink,
      },
      201
    );
  } catch (error) {
    const message =
      error instanceof Error ? error.message : 'Failed to create dashboard post';
    return c.json({ message }, 500);
  }
});

app.route('/api', api);
app.route('/internal', internal);

serve({
  fetch: app.fetch,
  createServer,
  port: getServerPort(),
});
