import type { FormField } from '@/types/form';
import { SafeDescription } from './SafeDescription';

interface ConsentFieldControlProps {
  answer: unknown;
  errorId?: string;
  field: FormField;
  fieldId: string;
  labelText: string;
  onChange: (value: unknown) => void;
}

export function ConsentFieldControl({
  answer,
  errorId,
  field,
  fieldId,
  labelText,
  onChange,
}: ConsentFieldControlProps) {
  const consents = field.consentSectionConfig?.consents ?? [];
  const selectedConsents = Array.isArray(answer) ? answer : [];

  return (
    <div
      aria-describedby={errorId}
      aria-invalid={Boolean(errorId) || undefined}
      aria-label={labelText}
      className='space-y-3'
      id={fieldId}
      role='group'
    >
      {consents.map((consent, index) => (
        <label className='flex cursor-pointer items-start gap-3' key={index}>
          <input
            checked={Boolean(selectedConsents[index])}
            className='mt-1 accent-blue-700'
            disabled={field.readOnly}
            onChange={(event) => {
              const nextValues = consents.map((_, currentIndex) =>
                currentIndex === index
                  ? event.target.checked
                  : Boolean(selectedConsents[currentIndex]),
              );
              onChange(nextValues);
            }}
            type='checkbox'
          />
          <span>
            <SafeDescription markup={consent.description} />
            {consent.required && (
              <span aria-label='wymagane' className='ml-1 text-red-700'>
                *
              </span>
            )}
          </span>
        </label>
      ))}
    </div>
  );
}