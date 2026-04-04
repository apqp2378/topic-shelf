import type {
  Candidate,
  CandidateDetailResponse,
  CandidateListResponse,
  CandidateMutationResponse,
  CandidateSort,
  CandidateStatus,
  CandidateStatusFilter,
  KeepExportResponse,
  RefreshCandidatesResponse,
} from '../types/candidate';

const readJson = async <T>(response: Response): Promise<T> => {
  const contentType = response.headers.get('content-type') ?? '';
  const isJson =
    contentType.includes('application/json') || contentType.includes('+json');

  if (!response.ok) {
    const fallbackMessage = `Request failed with status ${response.status}`;

    if (isJson) {
      try {
        const body: unknown = await response.json();
        if (typeof body === 'object' && body !== null) {
          const message = Reflect.get(body, 'message');
          if (typeof message === 'string') {
            throw new Error(message);
          }
        }
      } catch (error) {
        if (error instanceof Error) {
          throw error;
        }
      }
    }

    const errorText = await response.text();
    throw new Error(errorText.trim() || fallbackMessage);
  }

  if (!isJson) {
    const errorText = await response.text();
    throw new Error(errorText.trim() || 'Expected JSON response');
  }

  const data: T = await response.json();
  return data;
};

export const getCandidates = async (
  sort: CandidateSort,
  status: CandidateStatusFilter
): Promise<CandidateListResponse> =>
  readJson<CandidateListResponse>(
    await fetch(`/api/candidates?sort=${sort}&status=${status}`)
  );

export const getCandidate = async (candidateId: string): Promise<Candidate> => {
  const response = await readJson<CandidateDetailResponse>(
    await fetch(`/api/candidates/${candidateId}`)
  );

  return response.candidate;
};

export const updateCandidateStatus = async (
  candidateId: string,
  status: CandidateStatus
): Promise<Candidate> => {
  const response = await readJson<CandidateMutationResponse>(
    await fetch(`/api/candidates/${candidateId}/status`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ status }),
    })
  );

  return response.candidate;
};

export const updateCandidateNote = async (
  candidateId: string,
  reviewNote: string
): Promise<Candidate> => {
  const response = await readJson<CandidateMutationResponse>(
    await fetch(`/api/candidates/${candidateId}/note`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ review_note: reviewNote }),
    })
  );

  return response.candidate;
};

export const getKeepLinksExport = async (): Promise<KeepExportResponse> =>
  readJson<KeepExportResponse>(await fetch('/api/export/keep-links'));

export const getKeepMarkdownExport = async (): Promise<KeepExportResponse> =>
  readJson<KeepExportResponse>(await fetch('/api/export/keep-markdown'));

export const refreshCandidates = async (): Promise<RefreshCandidatesResponse> =>
  readJson<RefreshCandidatesResponse>(
    await fetch('/api/candidates/refresh', {
      method: 'POST',
    })
  );
