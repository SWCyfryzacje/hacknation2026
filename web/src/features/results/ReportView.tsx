import type { FormReport } from '@/types/report';

interface ReportViewProps {
  onDownloadDictionaries: () => void;
  report: FormReport;
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className='rounded-lg bg-white p-4'>
      <dt className='text-sm text-slate-500'>{label}</dt>
      <dd className='mt-1 font-semibold text-slate-900'>{value}</dd>
    </div>
  );
}

function Note({
  items,
  kind,
  title,
}: {
  items: string[];
  kind: 'error' | 'warning';
  title: string;
}) {
  return (
    <section
      className={`rounded-lg p-4 ${
        kind === 'error'
          ? 'bg-red-50 text-red-900'
          : 'bg-amber-50 text-amber-950'
      }`}
    >
      <h3 className='font-semibold'>{title}</h3>
      <ul className='mt-2 list-disc space-y-1 pl-5 text-sm'>
        {items.map((item, index) => (
          <li key={`${index}-${item}`}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

export function ReportView({
  onDownloadDictionaries,
  report,
}: ReportViewProps) {
  const analysis = report.analysis;
  const stats = report.stats;
  const usage = analysis?.llmUsage;
  const issues = report.issues ?? [];
  const warnings = report.warnings ?? [];
  const dictionaries = report.proposedDictionaries ?? [];

  return (
    <section className='space-y-6 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:p-6'>
      <div>
        <h3 className='text-lg font-semibold'>Szczegóły analizy</h3>
        <dl className='mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3'>
          <Stat
            label='Analiza'
            value={
              analysis?.analyzer === 'llm'
                ? `model językowy${analysis.model ? ` (${analysis.model})` : ''}`
                : analysis?.analyzer
                  ? 'reguły'
                  : '—'
            }
          />
          <Stat label='Urząd' value={analysis?.authority || '—'} />
          <Stat label='Strony' value={stats?.pages ?? '—'} />
          <Stat label='Sekcje' value={stats?.sections ?? '—'} />
          <Stat label='Pola' value={stats?.fields ?? '—'} />
          <Stat label='Pola warunkowe' value={stats?.conditional ?? '—'} />
          <Stat
            label='Czas'
            value={
              report.durationMs === undefined
                ? '—'
                : `${(report.durationMs / 1000).toFixed(1)} s`
            }
          />
          {report.extraction?.ocr && (
            <Stat label='OCR' value={report.extraction.ocrEngine || 'tak'} />
          )}
          {usage?.calls ? (
            <Stat
              label='Tokeny modelu'
              value={`${usage.prompt_tokens ?? 0} + ${usage.completion_tokens ?? 0}`}
            />
          ) : null}
        </dl>
      </div>

      <div className='space-y-3'>
        {issues.length > 0 && (
          <Note items={issues} kind='error' title='Problemy w konfiguracji:' />
        )}
        {warnings.length > 0 && (
          <Note items={warnings} kind='warning' title='Ostrzeżenia:' />
        )}
        {issues.length === 0 && warnings.length === 0 && (
          <p className='rounded-lg bg-emerald-50 p-4 text-emerald-900'>
            Konfiguracja przeszła kontrolę reguł bez uwag.
          </p>
        )}
      </div>

      {dictionaries.length > 0 && (
        <section>
          <div className='flex flex-col justify-between gap-3 sm:flex-row sm:items-center'>
            <h3 className='text-lg font-semibold'>Propozycje nowych słowników</h3>
            <button
              className='self-start rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700'
              onClick={onDownloadDictionaries}
              type='button'
            >
              Pobierz słowniki ({dictionaries.length})
            </button>
          </div>
          <div className='mt-3 overflow-x-auto rounded-lg border border-slate-200 bg-white'>
            <table className='min-w-full divide-y divide-slate-200 text-left text-sm'>
              <thead className='bg-slate-100 text-slate-700'>
                <tr>
                  <th className='px-4 py-3 font-semibold' scope='col'>
                    Słownik
                  </th>
                  <th className='px-4 py-3 font-semibold' scope='col'>
                    Wartości
                  </th>
                  <th className='px-4 py-3 font-semibold' scope='col'>
                    Używany w polach
                  </th>
                </tr>
              </thead>
              <tbody className='divide-y divide-slate-200'>
                {dictionaries.map((dictionary) => (
                  <tr key={dictionary.name}>
                    <th className='px-4 py-3 align-top font-medium' scope='row'>
                      <span className='font-semibold'>{dictionary.name}</span>
                      {dictionary.description && (
                        <p className='mt-1 text-slate-500'>
                          {dictionary.description}
                        </p>
                      )}
                    </th>
                    <td className='px-4 py-3 align-top'>
                      {dictionary.values.join(', ')}
                    </td>
                    <td className='px-4 py-3 align-top'>
                      {dictionary.used_by?.join(', ') || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </section>
  );
}