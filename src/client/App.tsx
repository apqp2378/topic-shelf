import { showToast } from '@devvit/web/client';
import { useEffect, useState } from 'react';
import {
  getCandidate,
  getCandidates,
  getKeepLinksExport,
  getKeepMarkdownExport,
  refreshCandidates,
  updateCandidateNote,
  updateCandidateStatus,
} from './api/client';
import { CandidateDetailPage } from './pages/CandidateDetailPage';
import { CandidateListPage } from './pages/CandidateListPage';
import { ExportPage } from './pages/ExportPage';
import type {
  Candidate,
  CandidateSort,
  CandidateStatus,
  CandidateStatusFilter,
} from './types/candidate';

type PageState =
  | { name: 'list' }
  | { name: 'detail'; candidateId: string }
  | { name: 'export' };

const copyText = async (value: string, successMessage: string): Promise<void> => {
  await navigator.clipboard.writeText(value);
  showToast(successMessage);
};

export const App = () => {
  const [page, setPage] = useState<PageState>({ name: 'list' });
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [noteDraft, setNoteDraft] = useState('');
  const [plainTextExport, setPlainTextExport] = useState('');
  const [markdownExport, setMarkdownExport] = useState('');
  const [keepCount, setKeepCount] = useState(0);
  const [sort, setSort] = useState<CandidateSort>('score');
  const [status, setStatus] = useState<CandidateStatusFilter>('all');
  const [subreddit, setSubreddit] = useState('');
  const [refreshedAt, setRefreshedAt] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const loadList = async (
    nextSort: CandidateSort = sort,
    nextStatus: CandidateStatusFilter = status
  ): Promise<void> => {
    setLoading(true);
    setError('');

    try {
      const response = await getCandidates(nextSort, nextStatus);
      setCandidates(response.candidates);
      setSubreddit(response.subreddit);
      setRefreshedAt(response.refreshed_at);
    } catch (loadError) {
      const message =
        loadError instanceof Error ? loadError.message : 'Failed to load candidates';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const loadDetail = async (candidateId: string): Promise<void> => {
    setSaving(true);
    setError('');

    try {
      const candidate = await getCandidate(candidateId);
      setSelectedCandidate(candidate);
      setNoteDraft(candidate.review_note);
      setPage({ name: 'detail', candidateId });
    } catch (loadError) {
      const message =
        loadError instanceof Error ? loadError.message : 'Failed to load candidate';
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  const loadExport = async (): Promise<void> => {
    setSaving(true);
    setError('');

    try {
      const [plainTextResponse, markdownResponse] = await Promise.all([
        getKeepLinksExport(),
        getKeepMarkdownExport(),
      ]);
      setPlainTextExport(plainTextResponse.content);
      setMarkdownExport(markdownResponse.content);
      setKeepCount(plainTextResponse.count);
      setPage({ name: 'export' });
    } catch (loadError) {
      const message =
        loadError instanceof Error ? loadError.message : 'Failed to load exports';
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    void (async () => {
      setLoading(true);
      setError('');

      try {
        const response = await getCandidates(sort, status);
        setCandidates(response.candidates);
        setSubreddit(response.subreddit);
        setRefreshedAt(response.refreshed_at);
      } catch (loadError) {
        const message =
          loadError instanceof Error ? loadError.message : 'Failed to load candidates';
        setError(message);
      } finally {
        setLoading(false);
      }
    })();
  }, [sort, status]);

  const handleRefresh = async (): Promise<void> => {
    setSaving(true);
    setError('');

    try {
      const result = await refreshCandidates();
      setRefreshedAt(result.refreshed_at);
      setSubreddit(result.subreddit);
      await loadList(sort, status);
      showToast(`Refreshed ${result.processed_count} candidates`);
    } catch (refreshError) {
      const message =
        refreshError instanceof Error ? refreshError.message : 'Refresh failed';
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  const syncCandidate = (updated: Candidate): void => {
    setCandidates((currentCandidates) =>
      currentCandidates.map((candidate) =>
        candidate.candidate_id === updated.candidate_id ? updated : candidate
      )
    );
    setSelectedCandidate((currentCandidate) =>
      currentCandidate?.candidate_id === updated.candidate_id ? updated : currentCandidate
    );
  };

  const handleCandidateStatusChange = async (
    candidateId: string,
    nextStatus: CandidateStatus
  ): Promise<void> => {
    setSaving(true);
    setError('');

    try {
      const updated = await updateCandidateStatus(candidateId, nextStatus);
      syncCandidate(updated);
      showToast(`Status updated to ${nextStatus}`);
    } catch (mutationError) {
      const message =
        mutationError instanceof Error ? mutationError.message : 'Failed to update status';
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveNote = async (): Promise<void> => {
    if (!selectedCandidate) {
      return;
    }

    setSaving(true);
    setError('');

    try {
      const updated = await updateCandidateNote(
        selectedCandidate.candidate_id,
        noteDraft
      );
      syncCandidate(updated);
      showToast('Review note saved');
    } catch (mutationError) {
      const message =
        mutationError instanceof Error ? mutationError.message : 'Failed to save note';
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  const handleSortChange = (nextSort: CandidateSort): void => {
    setSort(nextSort);
  };

  const handleStatusFilterChange = (nextStatus: CandidateStatusFilter): void => {
    setStatus(nextStatus);
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <div className="mx-auto max-w-6xl px-4 py-6">
        {error ? (
          <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        {page.name === 'list' ? (
          <CandidateListPage
            candidates={candidates}
            count={candidates.length}
            sort={sort}
            status={status}
            loading={loading || saving}
            refreshedAt={refreshedAt}
            subreddit={subreddit}
            onStatusChange={handleStatusFilterChange}
            onSortChange={handleSortChange}
            onRefresh={() => void handleRefresh()}
            onOpenExport={() => void loadExport()}
            onOpenDetail={(candidateId) => void loadDetail(candidateId)}
            onCandidateStatusChange={(candidateId, nextStatus) =>
              void handleCandidateStatusChange(candidateId, nextStatus)
            }
          />
        ) : null}

        {page.name === 'detail' && selectedCandidate ? (
          <CandidateDetailPage
            candidate={selectedCandidate}
            noteDraft={noteDraft}
            saving={saving}
            onBack={() => setPage({ name: 'list' })}
            onStatusChange={(nextStatus) =>
              void handleCandidateStatusChange(selectedCandidate.candidate_id, nextStatus)
            }
            onNoteDraftChange={setNoteDraft}
            onSaveNote={() => void handleSaveNote()}
          />
        ) : null}

        {page.name === 'export' ? (
          <ExportPage
            keepCount={keepCount}
            plainText={plainTextExport}
            markdown={markdownExport}
            loading={saving}
            onBack={() => setPage({ name: 'list' })}
            onCopyPlainText={() =>
              void copyText(plainTextExport, 'Plain text links copied')
            }
            onCopyMarkdown={() =>
              void copyText(markdownExport, 'Markdown links copied')
            }
          />
        ) : null}
      </div>
    </div>
  );
};
