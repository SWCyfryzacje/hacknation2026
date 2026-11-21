import { useState, type KeyboardEvent } from 'react';
import { ENABLE_JSON_DEBUG_VIEW } from '@/config/featureFlags';
import type { FormResult } from '@/types/form';
import { FormPreview } from '@/features/form-preview/FormPreview';
import { JsonDebugView } from './JsonDebugView';
import { ReportView } from './ReportView';
import { downloadJson } from './download';
import { getResultTabs, type ResultTab } from './resultTabs';

interface ResultPanelProps {
  onBackToUpload: () => void;
  result: FormResult;
}

function getBaseName(fileName: string): string {
  return fileName.replace(/\.[^.]+$/, '');
}

export function ResultPanel({ onBackToUpload, result }: ResultPanelProps) {
  const [activeTab, setActiveTab] = useState<ResultTab>('preview');
  const hasReport = result.report !== null;
  const tabs = getResultTabs(hasReport, ENABLE_JSON_DEBUG_VIEW);

  function handleTabKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;

    event.preventDefault();
    const activeIndex = tabs.findIndex((tab) => tab.id === activeTab);
    const offset = event.key === 'ArrowRight' ? 1 : -1;
    const nextTab = tabs[(activeIndex + offset + tabs.length) % tabs.length];
    setActiveTab(nextTab.id);
    document.getElementById(`result-tab-${nextTab.id}`)?.focus();
  }

  function downloadDictionaries() {
    if (!result.report?.proposedDictionaries?.length) return;
    downloadJson(
      { dictionaries: result.report.proposedDictionaries },
      `${getBaseName(result.sourceName)}.slowniki.json`,
    );
  }

  return (
    <section className='space-y-5 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-8'>
      <header className='flex flex-col justify-between gap-4 sm:flex-row sm:items-start'>
        <div>
          <p className='text-sm text-slate-500'>Źródło: {result.sourceName}</p>
          <h2 className='mt-1 text-xl font-semibold sm:text-2xl'>
            {result.form.title || 'Wynik przetwarzania dokumentu'}
          </h2>
        </div>
        <button
          className='self-start rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700'
          onClick={onBackToUpload}
          type='button'
        >
          Wróć do przesyłania
        </button>
      </header>

      <div
        aria-label='Widok wyniku'
        className='flex flex-wrap gap-2 border-b border-slate-200'
        onKeyDown={handleTabKeyDown}
        role='tablist'
      >
        {tabs.map((tab) => (
          <button
            aria-controls={`result-panel-${tab.id}`}
            aria-selected={activeTab === tab.id}
            className={`-mb-px border-b-2 px-3 py-3 text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 ${
              activeTab === tab.id
                ? 'border-blue-700 text-blue-800'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
            id={`result-tab-${tab.id}`}
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            role='tab'
            tabIndex={activeTab === tab.id ? 0 : -1}
            type='button'
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div
        aria-labelledby='result-tab-preview'
        className='min-w-0'
        hidden={activeTab !== 'preview'}
        id='result-panel-preview'
        role='tabpanel'
        tabIndex={0}
      >
        <FormPreview form={result.form} report={result.report} />
      </div>

      {hasReport && result.report && (
        <div
          aria-labelledby='result-tab-report'
          className='min-w-0'
          hidden={activeTab !== 'report'}
          id='result-panel-report'
          role='tabpanel'
          tabIndex={0}
        >
          <ReportView
            onDownloadDictionaries={downloadDictionaries}
            report={result.report}
          />
        </div>
      )}

      {ENABLE_JSON_DEBUG_VIEW && (
        <div
          aria-labelledby='result-tab-json'
          className='min-w-0'
          hidden={activeTab !== 'json'}
          id='result-panel-json'
          role='tabpanel'
          tabIndex={0}
        >
          <JsonDebugView form={result.form} sourceName={result.sourceName} />
        </div>
      )}
    </section>
  );
}