type ExportPageProps = {
  keepCount: number;
  plainText: string;
  markdown: string;
  loading: boolean;
  onBack: () => void;
  onCopyPlainText: () => void;
  onCopyMarkdown: () => void;
};

export const ExportPage = ({
  keepCount,
  plainText,
  markdown,
  loading,
  onBack,
  onCopyPlainText,
  onCopyMarkdown,
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
      <span className="rounded-md bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-800">
        Keep candidates: {keepCount}
      </span>
    </div>

    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Plain text export</h1>
          <p className="mt-1 text-sm text-slate-500">
            Newline-separated links for manual downstream use.
          </p>
        </div>
        <button
          type="button"
          disabled={loading}
          onClick={onCopyPlainText}
          className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white"
        >
          Copy plain text
        </button>
      </div>
      <textarea
        readOnly
        value={plainText}
        rows={10}
        className="mt-4 w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 font-mono text-sm text-slate-800"
      />
    </section>

    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Markdown export</h2>
          <p className="mt-1 text-sm text-slate-500">
            Markdown bullet list of the same keep links.
          </p>
        </div>
        <button
          type="button"
          disabled={loading}
          onClick={onCopyMarkdown}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700"
        >
          Copy markdown
        </button>
      </div>
      <textarea
        readOnly
        value={markdown}
        rows={10}
        className="mt-4 w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 font-mono text-sm text-slate-800"
      />
    </section>
  </div>
);
