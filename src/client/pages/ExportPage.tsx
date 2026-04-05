type ExportPageProps = {
  keepCount: number;
  refreshedAt: number | null;
  plainText: string;
  markdown: string;
  rawJson: string;
  loading: boolean;
  onBack: () => void;
  onCopyPlainText: () => void;
  onCopyMarkdown: () => void;
  onCopyRawJson: () => void;
};

const formatRefreshTime = (value: number | null): string => {
  if (!value) {
    return 'Not available';
  }

  return new Date(value).toLocaleString();
};

const renderBody = (title: string, description: string, value: string, buttonLabel: string, onCopy: () => void, disabled: boolean) => (
  <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
    <div className="flex items-center justify-between gap-3">
      <div>
        <h2 className="text-xl font-bold text-slate-900">{title}</h2>
        <p className="mt-1 text-sm text-slate-500">{description}</p>
      </div>
      <button
        type="button"
        disabled={disabled}
        onClick={onCopy}
        className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700"
      >
        {buttonLabel}
      </button>
    </div>
    <textarea
      readOnly
      value={value}
      rows={12}
      className="mt-4 w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 font-mono text-sm text-slate-800"
    />
  </section>
);

export const ExportPage = ({
  keepCount,
  refreshedAt,
  plainText,
  markdown,
  rawJson,
  loading,
  onBack,
  onCopyPlainText,
  onCopyMarkdown,
  onCopyRawJson,
}: ExportPageProps) => (
  <div className="space-y-4">
    <div className="flex items-center justify-between gap-3">
      <button
        type="button"
        onClick={onBack}
        className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700"
      >
        Back to list
      </button>
      <div className="flex flex-wrap gap-2">
        <span className="rounded-md bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-800">
          Keep candidates: {keepCount}
        </span>
        <span className="rounded-md bg-slate-100 px-3 py-2 text-sm font-semibold text-slate-700">
          Last refresh: {formatRefreshTime(refreshedAt)}
        </span>
      </div>
    </div>

    {renderBody(
      'Plain text export',
      'Title plus link pairs for quick copy into the Python project.',
      plainText,
      'Copy plain text',
      onCopyPlainText,
      loading
    )}

    {renderBody(
      'Markdown export',
      'Bullet list with titles and nested links.',
      markdown,
      'Copy markdown',
      onCopyMarkdown,
      loading
    )}

    {renderBody(
      'Raw JSON export',
      'Raw JSON array for validating keep candidates before handing them to Python.',
      rawJson,
      'Copy raw JSON',
      onCopyRawJson,
      loading
    )}
  </div>
);
