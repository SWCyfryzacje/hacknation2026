import type { ReactNode } from 'react';
import type { FormField } from '@/types/form';
import type { ProposedDictionary } from '@/types/report';
import {
  getDictionaryHint,
  getFieldOptions,
} from './utils';
import { getFieldRules } from './validators';
import { SafeDescription } from './SafeDescription';
import { hasDescriptionText } from './descriptionUtils';
import { ChoiceFieldControl } from './ChoiceFieldControl';
import { ConsentFieldControl } from './ConsentFieldControl';

interface FieldRendererProps {
  answer: unknown;
  dictionaries: ProposedDictionary[];
  error?: string;
  field: FormField;
  onChange: (value: unknown) => void;
  readOnlyOverride?: boolean;
  showTechName: boolean;
}

function displayValue(value: unknown): string {
  return typeof value === 'string' || typeof value === 'number'
    ? String(value)
    : '';
}

function TechName({ name, show }: { name: string; show: boolean }) {
  return (
    <span className='ml-2 text-xs font-normal text-slate-400' hidden={!show}>
      {name}
    </span>
  );
}

function FieldMeta({ readOnly }: { readOnly: boolean }) {
  return (
    <>
      {readOnly && (
        <span className='ml-2 inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600'>
          tylko do odczytu
        </span>
      )}
    </>
  );
}

export function FieldRenderer({
  answer,
  dictionaries,
  error,
  field,
  onChange,
  readOnlyOverride = false,
  showTechName,
}: FieldRendererProps) {
  const fieldId = `control-${field.id}`;
  const errorId = `error-${field.id}`;
  const rules = getFieldRules(field);
  const required = rules.includes('REQUIRED');
  const labelText =
    field.title ||
    (field.type === 'CONSENT_SECTION' ? 'Zgody i oświadczenia' : field.techName);
  const options = getFieldOptions(field, dictionaries);
  const isReadOnly = Boolean(field.readOnly || readOnlyOverride);
  const renderedField = isReadOnly ? { ...field, readOnly: true } : field;
  const hasErrorProps = error
    ? { 'aria-invalid': true as const, 'aria-describedby': errorId }
    : {};

  if (field.type === 'TEXT_BLOCK' || field.type === 'INFO_SECTION') {
    return (
      <div className='rounded-lg bg-blue-50/60 p-4 text-slate-700'>
        <div className='prose prose-sm max-w-none'>
          <SafeDescription markup={field.description} />
        </div>
        <TechName name={field.techName} show={showTechName} />
      </div>
    );
  }

  let control: ReactNode;

  switch (field.type) {
    case 'TEXTAREA':
      control = (
        <textarea
          className='min-h-28 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100'
          id={fieldId}
          onChange={(event) => onChange(event.target.value)}
          readOnly={isReadOnly}
          value={displayValue(answer)}
          {...hasErrorProps}
        />
      );
      break;
    case 'NUMBER':
    case 'DATEPICKER':
    case 'TEXT_FIELD': {
      const inputType =
        field.type === 'NUMBER'
          ? 'number'
          : field.type === 'DATEPICKER'
            ? 'date'
            : rules.includes('EMAIL')
              ? 'email'
              : 'text';
      const placeholder = rules.includes('ZIP_CODE')
        ? '__-___'
        : field.tooltipMessage;

      control = (
        <input
          className='w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100 read-only:bg-slate-100'
          id={fieldId}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          readOnly={isReadOnly}
          type={inputType}
          value={displayValue(answer)}
          {...hasErrorProps}
        />
      );
      break;
    }
    case 'RADIO':
    case 'CHECKBOX':
      control = (
        <ChoiceFieldControl
          answer={answer}
          errorId={error ? errorId : undefined}
          field={renderedField}
          fieldId={fieldId}
          labelText={labelText}
          onChange={onChange}
          options={options}
        />
      );
      break;
    case 'SELECT':
      control = options ? (
        <select
          className='w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100'
          disabled={isReadOnly}
          id={fieldId}
          onChange={(event) => onChange(event.target.value || undefined)}
          value={displayValue(answer)}
          {...hasErrorProps}
        >
          <option value=''>— wybierz —</option>
          {options.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      ) : (
        <input
          className='w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100 read-only:bg-slate-100'
          id={fieldId}
          onChange={(event) => onChange(event.target.value)}
          placeholder={getDictionaryHint(field)}
          readOnly={isReadOnly}
          value={displayValue(answer)}
          {...hasErrorProps}
        />
      );
      break;
    case 'FILE_UPLOADER':
      control = (
        <div className='space-y-2'>
          <input
            className='block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-blue-50 file:px-3 file:py-2 file:font-semibold file:text-blue-800 hover:file:bg-blue-100 disabled:opacity-60'
            disabled={isReadOnly}
            id={fieldId}
            onChange={(event) => onChange(event.target.files?.[0]?.name)}
            type='file'
            {...hasErrorProps}
          />
          {typeof answer === 'string' && (
            <p className='text-sm text-slate-600'>Wybrano: {answer}</p>
          )}
        </div>
      );
      break;
    case 'CONSENT_SECTION':
      control = (
        <ConsentFieldControl
          answer={answer}
          errorId={error ? errorId : undefined}
          field={renderedField}
          fieldId={fieldId}
          labelText={labelText}
          onChange={onChange}
        />
      );
      break;
    default:
      control = (
        <p className='text-sm text-slate-500'>
          Nieobsługiwany typ pola: {field.type}
        </p>
      );
  }

  const grouped = ['RADIO', 'CHECKBOX', 'CONSENT_SECTION'].includes(field.type);
  const label = (
    <>
      {labelText}
      {required && <span className='ml-1 text-red-700'>*</span>}
      <TechName name={field.techName} show={showTechName} />
      <FieldMeta readOnly={isReadOnly} />
    </>
  );

  return (
    <div className='space-y-2'>
      {grouped ? (
        <fieldset
          aria-required={required}
          className='space-y-3'
          disabled={isReadOnly}
        >
          <legend className='mb-2 font-semibold text-slate-800'>{label}</legend>
          {hasDescriptionText(field.description) && (
            <div className='text-sm leading-6 text-slate-600'>
              <SafeDescription markup={field.description} />
            </div>
          )}
          {control}
        </fieldset>
      ) : (
        <>
          <label className='block font-semibold text-slate-800' htmlFor={fieldId}>
            {label}
          </label>
          {hasDescriptionText(field.description) && (
            <div className='text-sm leading-6 text-slate-600'>
              <SafeDescription markup={field.description} />
            </div>
          )}
          {field.tooltipMessage && (
            <p className='text-sm text-slate-500'>{field.tooltipMessage}</p>
          )}
          {control}
        </>
      )}
      {error && (
        <p className='text-sm text-red-700' id={errorId} role='alert'>
          {error}
        </p>
      )}
    </div>
  );
}