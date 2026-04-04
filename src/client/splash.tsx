import './index.css';

import { requestExpandedMode } from '@devvit/web/client';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

export const Splash = () => (
  <div className="flex min-h-screen items-center justify-center bg-slate-100 px-4 py-8">
    <div className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
        Internal moderation tool
      </p>
      <h1 className="mt-2 text-3xl font-bold text-slate-900">
        Reddit candidate picker
      </h1>
      <p className="mt-3 text-sm leading-6 text-slate-600">
        Review recent subreddit posts, apply explicit keep or review decisions, and export the `keep` set for manual downstream use.
      </p>
      <button
        type="button"
        onClick={(event) => requestExpandedMode(event.nativeEvent, 'game')}
        className="mt-6 rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
      >
        Open dashboard
      </button>
    </div>
  </div>
);

const rootElement = document.getElementById('root');

if (rootElement) {
  createRoot(rootElement).render(
    <StrictMode>
      <Splash />
    </StrictMode>
  );
}
