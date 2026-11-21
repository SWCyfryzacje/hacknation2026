import { useMemo, useState } from 'react';
import type { FormConfiguration } from '@/types/form';
import { downloadJson } from './download';

interface JsonDebugViewProps {
  form: FormConfiguration;
  sourceName: string;
}

function getBaseName(fileName: string): string {
  return fileName.replace(/\.[^.]+$/, '');
}

export function JsonDebugView({ form, sourceName }: JsonDebugViewProps) {
  const [copyStatus, setCopyStatus] = useState('');
  const json = useMemo(() => JSON.stringify(form, null, 2), [form]);
  const baseName = getBaseName(sourceName);

  async function copyJson() {
    try {
      await navigator.clipboard.writeText(json);
      setCopyStatus('Skopiowano.');
    } catch {
      setCopyStatus('Nie udało się skopiować — zaznacz tekst ręcznie.');
    }
  }

  return (
    <section className='space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:p-6'>
      <div className='flex flex-wrap items-center gap-3'>
        <button
          className='rounded-lg bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700'
          onClick={() => downloadJson(form, `${baseName}.json`)}
          type='button'
        >
          Pobierz JSON
        </button>
        <button
          className='rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700'
          onClick={() => void copyJson()}
          type='button'
        >
          Kopiuj JSON
        </button>
        <span aria-live='polite' className='text-sm text-slate-600' role='status'>
          {copyStatus}
        </span>
      </div>
      <pre
        aria-label='Wygenerowany JSON'
        className='max-h-[70vh] overflow-auto rounded-lg bg-slate-950 p-4 text-xs leading-5 text-slate-100 sm:text-sm'
        tabIndex={0}
      >
        {json}
      </pre>
    </section>
  );
}