import type { FormField } from '@/types/form';
import { getDictionaryHint } from './utils';

interface ChoiceFieldControlProps {
  answer: unknown;
  errorId?: string;
  field: FormField;
  fieldId: string;
  labelText: string;
  onChange: (value: unknown) => void;
  options: string[] | null;
}

export function ChoiceFieldControl({
  answer,
  errorId,
  field,
  fieldId,
  labelText,
  onChange,
  options,
}: ChoiceFieldControlProps) {
  if (!options) {
    return <p className='text-sm text-slate-500'>{getDictionaryHint(field)}</p>;
  }

  const isMultiple = field.type === 'CHECKBOX';
  const selectedValues = Array.isArray(answer) ? answer : [];

  return (
    <div
      aria-describedby={errorId}
      aria-invalid={Boolean(errorId) || undefined}
      aria-label={labelText}
      className='space-y-2'
      id={fieldId}
      role={isMultiple ? 'group' : 'radiogroup'}
    >
      {options.map((option) => (
        <label className='flex cursor-pointer items-start gap-3' key={option}>
          <input
            checked={
              isMultiple ? selectedValues.includes(option) : answer === option
            }
            className='mt-1 accent-blue-700'
            disabled={field.readOnly}
            name={fieldId}
            onChange={(event) => {
              if (isMultiple) {
                const nextValues = event.target.checked
                  ? [...selectedValues, option]
                  : selectedValues.filter((value) => value !== option);
                onChange(nextValues);
              } else {
                onChange(option);
              }
            }}
            type={isMultiple ? 'checkbox' : 'radio'}
            value={option}
          />
          <span>{option}</span>
        </label>
      ))}
    </div>
  );
}