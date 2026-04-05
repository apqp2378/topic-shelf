import type { Candidate } from '../../shared/candidate';

export const DASHBOARD_POST_TITLE = 'Candidate Picker Dashboard';

const normalizeText = (value: string): string =>
  value.replace(/\s+/g, ' ').trim().toLowerCase();

export const isDashboardPostTitle = (title: string): boolean =>
  normalizeText(title) === normalizeText(DASHBOARD_POST_TITLE);

export const getExcludedCandidateReason = (
  candidate: Pick<Candidate, 'title' | 'author'>,
  appUserName?: string
): string | null => {
  if (isDashboardPostTitle(candidate.title)) {
    return 'dashboard_post_title';
  }

  if (appUserName && normalizeText(candidate.author) === normalizeText(appUserName)) {
    return 'app_user_post';
  }

  return null;
};

export const isExcludedPersistedCandidate = (
  candidate: Pick<Candidate, 'title'>
): boolean => isDashboardPostTitle(candidate.title);
