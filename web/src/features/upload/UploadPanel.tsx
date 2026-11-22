import { useEffect, useRef, useState } from 'react';
import { ApiError, convertDocument, getReadableError } from '@/services/api';
import { isFormConfiguration, type FormResult } from '@/types/form';
import { isFormReport } from '@/types/report';
import {
  allowedDocumentExtensions,
  validateDocumentFile,
} from './fileValidation';
import { readFormFile } from './formFile';

interface UploadPanelProps {
  authRequired: boolean;
  token: string | null;
  onFormReady: (result: FormResult) => void;
  onSessionExpired: () => void;
}

function validateConversionResponse(value: unknown): FormResult['form'] {
  if (
    typeof value === 'object' &&
    value !== null &&
    'form' in value &&
    isFormConfiguration(value.form)
  ) {
    return value.form;
  }

  throw new Error('Serwer nie zwrócił prawidłowej konfiguracji formularza.');
}

export function UploadPanel({
  authRequired,
  token,
  onFormReady,
  onSessionExpired,
}: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const jsonInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (!isUploading) return;

    const timer = window.setInterval(() => {
      setElapsedSeconds((elapsed) => elapsed + 1);
    }, 1000);

    return () => window.clearInterval(timer);
  }, [isUploading]);

  function chooseFile(file: File | null) {
    const validationError = file ? validateDocumentFile(file) : null;
    setError(validationError);
    setSelectedFile(file && !validationError ? file : null);
  }

  function handleDrop(event: React.DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(false);

    if (event.dataTransfer.files.length > 1) {
      setSelectedFile(null);
      setError('Wgraj jeden plik na raz.');
      return;
    }

    chooseFile(event.dataTransfer.files[0] ?? null);
  }

  async function handleConvert() {
    if (!selectedFile || isUploading) return;

    setError(null);
    setElapsedSeconds(0);
    setIsUploading(true);

    try {
      const response = await convertDocument(selectedFile, authRequired, token);
      const form = validateConversionResponse(response);
      const reportValue =
        typeof response === 'object' && response !== null && 'report' in response
          ? response.report ?? null
          : null;
      const report = isFormReport(reportValue) ? reportValue : null;

      onFormReady({ form, report, sourceName: selectedFile.name });
    } catch (requestError: unknown) {
      if (
        requestError instanceof ApiError &&
        requestError.status === 401 &&
        authRequired
      ) {
        onSessionExpired();
        return;
      }

      setError(
        getReadableError(requestError, 'Nie można połączyć się z serwerem.'),
      );
    } finally {
      setIsUploading(false);
    }
  }

  async function handleJsonFile(file: File | null) {
    if (!file) return;

    setError(null);
    try {
      onFormReady(await readFormFile(file));
    } catch (readError: unknown) {
      const detail =
        readError instanceof Error
          ? readError.message
          : 'Nie można odczytać pliku.';
      setError(`To nie jest poprawna konfiguracja formularza: ${detail}`);
    }
  }

  return (
    <section className='rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8'>
      <h2 className='text-xl font-semibold'>Prześlij dokument</h2>
      <p className='mt-2 text-sm leading-6 text-slate-600'>
        Wybierz dokument do przetworzenia. Możesz przesłać plik PDF, DOC, DOCX,
        ODS, XLSX, JPG, JPEG lub PNG.
      </p>

      <label
        className={`mt-6 flex min-h-48 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-5 py-8 text-center transition-colors focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-blue-700 ${
          isDragging
            ? 'border-blue-700 bg-blue-50'
            : 'border-slate-300 bg-slate-50 hover:border-blue-500 hover:bg-blue-50/50'
        }`}
        htmlFor='document-file'
        onDragLeave={() => setIsDragging(false)}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDrop={handleDrop}
      >
        <span aria-hidden='true' className='text-3xl text-blue-700'>
          ↑
        </span>
        <span className='mt-3 font-semibold'>
          Kliknij, aby wybrać plik lub przeciągnij go tutaj
        </span>
        <span className='mt-1 text-sm text-slate-500'>Jeden plik na raz</span>
        <input
          accept={allowedDocumentExtensions.join(',')}
          className='sr-only'
          id='document-file'
          onChange={(event) => {
            chooseFile(event.currentTarget.files?.[0] ?? null);
            event.currentTarget.value = '';
          }}
          ref={inputRef}
          type='file'
        />
      </label>

      {selectedFile && (
        <p className='mt-4 text-sm text-slate-700'>
          Wybrany plik: <span className='font-semibold'>{selectedFile.name}</span>{' '}
          ({(selectedFile.size / 1024).toFixed(0)} KB)
        </p>
      )}

      {error && (
        <p aria-live='polite' className='mt-4 text-sm text-red-700' role='alert'>
          {error}
        </p>
      )}

      {isUploading && (
        <p aria-live='polite' className='mt-4 text-sm font-medium text-blue-800'>
          <span aria-hidden='true' className='mr-2 inline-block animate-spin'>
            ◌
          </span>
          Analiza… {elapsedSeconds} s
        </p>
      )}

      <div className='mt-6 flex flex-col gap-3 sm:flex-row sm:items-center'>
        <button
          className='rounded-lg bg-blue-700 px-5 py-3 font-semibold text-white hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 disabled:cursor-not-allowed disabled:opacity-50'
          disabled={!selectedFile || isUploading}
          onClick={handleConvert}
          type='button'
        >
          {isUploading ? 'Przetwarzanie…' : 'Przetwórz dokument'}
        </button>
        <button
          className='rounded-lg border border-slate-300 px-5 py-3 font-semibold hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 disabled:cursor-not-allowed disabled:opacity-50'
          disabled={isUploading}
          onClick={() => jsonInputRef.current?.click()}
          type='button'
        >
          Otwórz istniejący formularz JSON
        </button>
        <input
          accept='.json,application/json'
          className='sr-only'
          onChange={(event) => {
            void handleJsonFile(event.currentTarget.files?.[0] ?? null);
            event.currentTarget.value = '';
          }}
          ref={jsonInputRef}
          type='file'
        />
      </div>
    </section>
  );
}