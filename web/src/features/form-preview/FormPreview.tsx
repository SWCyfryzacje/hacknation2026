import { useEffect, useMemo, useRef, useState } from 'react';
import type { FormConfiguration, FormField, FormResult } from '@/types/form';
import { FieldRenderer } from './FieldRenderer';
import { SafeDescription } from './SafeDescription';
import { isUserVisibleField, orderTabs, sortByPosition } from './utils';
import { isInputField, validateField } from './validators';
import { evaluateVisibility } from './visibility';

interface FormPreviewProps {
  form: FormConfiguration;
  report: FormResult['report'];
  answers: Record<string, unknown>;
  pageIndex: number;
  showTechNames: boolean;
  onAnswersChange: (answers: Record<string, unknown>) => void;
  onPageIndexChange: (pageIndex: number) => void;
  onShowTechNamesChange: (showTechNames: boolean) => void;
}

function isSection(field: FormField): boolean {
  return (
    field.type === 'SECTION' ||
    field.type === 'REPEATING_SECTION' ||
    Boolean(field.repeatingSectionGrid?.length)
  );
}

export function FormPreview({
  form,
  report,
  answers,
  pageIndex,
  showTechNames,
  onAnswersChange,
  onPageIndexChange,
  // onShowTechNamesChange,
}: FormPreviewProps) {
  const pages = useMemo(() => orderTabs(form), [form]);
  const dictionaries = useMemo(
    () => report?.proposedDictionaries ?? [],
    [report],
  );
  const [visibleFields, setVisibleFields] = useState<Record<string, boolean>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const fieldElements = useRef(new Map<string, HTMLDivElement>());

  useEffect(() => {
    let isCurrent = true;

    evaluateVisibility(form, answers).then((visibility) => {
      if (!isCurrent) return;
      setVisibleFields(visibility);
      setErrors((previous) =>
        Object.fromEntries(
          Object.entries(previous).filter(([fieldId]) => visibility[fieldId] !== false),
        ),
      );
    });

    return () => {
      isCurrent = false;
    };
  }, [answers, form]);

  function isVisible(field: FormField): boolean {
    return visibleFields[field.id] !== false;
  }

  function handleAnswerChange(field: FormField, value: unknown) {
    const nextAnswers = { ...answers };
    if (value === undefined) delete nextAnswers[field.techName];
    else nextAnswers[field.techName] = value;
    onAnswersChange(nextAnswers);
    setErrors((previous) => {
      if (!(field.id in previous)) return previous;
      const next = { ...previous };
      delete next[field.id];
      return next;
    });
  }

  function renderField(field: FormField): React.ReactNode {
    if (!isUserVisibleField(field)) return null;

    if (isSection(field)) {
      const headingId = `section-heading-${field.id}`;
      return (
        <section
          aria-labelledby={headingId}
          className='mt-5 space-y-5 rounded-xl border border-slate-200 bg-white p-4 sm:p-6'
          hidden={!isVisible(field)}
          key={field.id}
        >
          <h3 className='text-lg font-semibold text-slate-900' id={headingId}>
            {field.title || field.techName}
            {showTechNames && (
              <span className='ml-2 text-xs font-normal text-slate-400'>
                {field.techName}
              </span>
            )}
            {field.type === 'REPEATING_SECTION' && (
              <span className='ml-2 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600'>
                sekcja powtarzalna
              </span>
            )}
          </h3>
          <div className='text-sm leading-6 text-slate-600'>
            <SafeDescription markup={field.description} />
          </div>
          {sortByPosition(field.repeatingSectionGrid ?? []).map((item) =>
            renderField(item.field),
          )}
        </section>
      );
    }

    return (
      <div
        className='mt-5 rounded-xl border border-slate-200 bg-white p-4 sm:p-6'
        hidden={!isVisible(field)}
        key={field.id}
        ref={(element) => {
          if (element) fieldElements.current.set(field.id, element);
          else fieldElements.current.delete(field.id);
        }}
      >
        <FieldRenderer
          answer={answers[field.techName]}
          dictionaries={dictionaries}
          error={errors[field.id]}
          field={field}
          onChange={(value) => handleAnswerChange(field, value)}
          showTechName={showTechNames}
        />
      </div>
    );
  }

  function getPageFields(): FormField[] {
    const fields: FormField[] = [];

    function addVisibleFields(field: FormField, ancestorsVisible: boolean) {
      if (
        !ancestorsVisible ||
        !isVisible(field) ||
        !isUserVisibleField(field)
      ) {
        return;
      }
      if (isInputField(field)) fields.push(field);
      for (const child of field.repeatingSectionGrid ?? []) {
        addVisibleFields(child.field, true);
      }
    }

    for (const question of pages[pageIndex]?.questions ?? []) {
      addVisibleFields(question.field, true);
    }
    return fields;
  }

  function validateCurrentPage(): boolean {
    const fields = getPageFields();
    const nextErrors = { ...errors };
    let firstInvalidField: FormField | null = null;

    for (const field of fields) {
      if (field.readOnly) continue;
      const message = validateField(field, answers[field.techName]);
      if (message) {
        nextErrors[field.id] = message;
        firstInvalidField ??= field;
      } else {
        delete nextErrors[field.id];
      }
    }

    setErrors(nextErrors);
    if (!firstInvalidField) return true;

    const element = fieldElements.current.get(firstInvalidField.id);
    element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    element
      ?.querySelector<HTMLElement>('input, select, textarea, button')
      ?.focus();
    return false;
  }

  function goToPage(index: number) {
    if (index < 0 || index >= pages.length) return;
    onPageIndexChange(index);
  }

  const currentPage = pages[pageIndex];
  const progress = pages.length ? ((pageIndex + 1) / pages.length) * 100 : 0;

  return (
    <section className='rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm sm:p-8'>
      {pages.length === 0 ? (
        <p className='mt-8 rounded-lg bg-amber-50 p-4 text-amber-900'>
          Ta konfiguracja nie zawiera stron formularza.
        </p>
      ) : (
        <>
          {/*<label className='mt-6 inline-flex items-center gap-2 text-sm text-slate-600'>*/}
          {/*  <input*/}
          {/*    checked={showTechNames}*/}
          {/*    className='accent-blue-700'*/}
          {/*    onChange={(event) => onShowTechNamesChange(event.target.checked)}*/}
          {/*    type='checkbox'*/}
          {/*  />*/}
          {/*  Pokaż nazwy techniczne*/}
          {/*</label>*/}

          <nav aria-label='Strony formularza' className='mt-6 overflow-x-auto'>
            <ol className='flex min-w-max gap-2 pb-2'>
              {pages.map((page, index) => (
                <li key={page.id ?? `${page.title ?? 'page'}-${index}`}>
                  <button
                    aria-current={index === pageIndex ? 'step' : undefined}
                    className={`rounded-lg px-3 py-2 text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 ${
                      index === pageIndex
                        ? 'bg-blue-700 text-white'
                        : 'bg-white text-slate-700 hover:bg-blue-50'
                    }`}
                    onClick={() => goToPage(index)}
                    type='button'
                  >
                    <span className='mr-2'>{index + 1}.</span>
                    {page.title || `Strona ${index + 1}`}
                  </button>
                </li>
              ))}
            </ol>
          </nav>

          {currentPage && (
            <div className='mt-3 rounded-xl border border-slate-200 bg-slate-100 p-4 sm:p-6'>
              <p className='text-sm font-semibold text-blue-800'>
                Krok {pageIndex + 1} z {pages.length}
                {currentPage.type === 'FINISH' ? ' — strona końcowa' : ''}
              </p>
              <div
                aria-label={`Postęp formularza: ${pageIndex + 1} z ${pages.length}`}
                aria-valuemax={pages.length}
                aria-valuemin={1}
                aria-valuenow={pageIndex + 1}
                className='mt-3 h-2 overflow-hidden rounded-full bg-slate-200'
                role='progressbar'
              >
                <div
                  className='h-full rounded-full bg-blue-700 transition-all'
                  style={{ width: `${progress}%` }}
                />
              </div>
              <h3 className='mt-5 text-lg font-semibold text-slate-900'>
                {currentPage.title}
              </h3>

              <div className='mt-4'>
                {sortByPosition(currentPage.questions ?? []).map((question, index) =>
                  renderField(question.field) ?? (
                    <span key={`empty-question-${index}`} />
                  ),
                )}
              </div>

              <div className='mt-8 flex flex-wrap items-center justify-between gap-3'>
                <button
                  className='rounded-lg border border-slate-300 bg-white px-4 py-2.5 font-semibold hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 disabled:cursor-not-allowed disabled:opacity-50'
                  disabled={pageIndex === 0}
                  onClick={() => goToPage(pageIndex - 1)}
                  type='button'
                >
                  Wstecz
                </button>
                {pageIndex < pages.length - 1 ? (
                  <button
                    className='rounded-lg bg-blue-700 px-5 py-2.5 font-semibold text-white hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700'
                    onClick={() => {
                      if (validateCurrentPage()) goToPage(pageIndex + 1);
                    }}
                    type='button'
                  >
                    Dalej
                  </button>
                ) : (
                  <p className='text-sm text-slate-600'>
                    W systemie docelowym tutaj następuje podpis i wysłanie wniosku.
                  </p>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}