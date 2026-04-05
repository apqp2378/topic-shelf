## Reddit Candidate Picker V1

Internal moderator-facing Devvit Web dashboard for reviewing recent posts in a test subreddit, scoring them with explicit rules, preserving human moderation decisions in Redis, and exporting `keep` candidates for manual downstream use.

## Setup

1. Install dependencies with `npm install`
2. Update `devvit.json` if you want a different development subreddit than `your_test_subreddit`
3. Log in with `npm run login`
4. Start the app with `npm run dev`
5. From the subreddit menu, use `Open candidate picker dashboard` to create the dashboard post

## Commands

- `npm run dev`: Start local Devvit playtest mode
- `npm run build`: Build client and server bundles
- `npm run type-check`: Run TypeScript project references
- `npm run lint`: Run ESLint
- `npm run test -- my-file-name`: Run a specific Vitest file

## Pages

- `CandidateListPage`: Main moderation queue with status filter, score/latest/comment sorting, quick status actions, manual refresh, and detail navigation
- `CandidateDetailPage`: Full candidate review view with metadata, reason tags, top comments, status controls, and moderator review note editing
- `ExportPage`: Shows the current `keep` set and provides plain-text and Markdown copy actions with title + link formatting

## Scheduler

- `refresh-candidates` runs every 2 hours via `/internal/scheduler/refresh-candidates`
- The refresh fetches 30 recent posts plus top 5 comments per post from the installed subreddit
- Candidate content, metrics, score, and reason tags are refreshed
- Human-entered `status` and `review_note` are preserved and never overwritten
- Recommended status is shown alongside moderator status in list and detail views
- Export endpoints include `/api/export/keep-links`, `/api/export/keep-markdown`, and `/api/export/keep-raw-json`

## Run Checklist

- `devvit.json` points at your test subreddit
- The app is installed in that subreddit
- The moderator dashboard post opens successfully
- Candidate refresh returns recent subreddit posts
- Status and review note updates persist across refreshes
- Export copy actions return the expected `keep` links
