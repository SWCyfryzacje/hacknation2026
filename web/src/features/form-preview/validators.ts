import type { FormField } from '@/types/form';

const inputFieldTypes = new Set([
  'TEXT_FIELD',
  'TEXTAREA',
  'NUMBER',
  'DATEPICKER',
  'RADIO',
  'CHECKBOX',
  'SELECT',
  'FILE_UPLOADER',
  'CONSENT_SECTION',
]);

const validators: Partial<Record<string, (value: string) => string | null>> = {
  PESEL(value) {
    const digits = value.replace(/[\s-]/g, '');
    if (!/^\d{11}$/.test(digits)) return 'Numer PESEL ma 11 cyfr.';
    const checksum = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3].reduce(
      (sum, weight, index) => sum + weight * Number(digits[index]),
      0,
    );
    return (10 - (checksum % 10)) % 10 === Number(digits[10])
      ? null
      : 'Nieprawidłowy numer PESEL.';
  },
  NIP(value) {
    const digits = value.replace(/[\s-]/g, '');
    if (!/^\d{10}$/.test(digits)) return 'NIP ma 10 cyfr.';
    const checksum =
      [6, 5, 7, 2, 3, 4, 5, 6, 7].reduce(
        (sum, weight, index) => sum + weight * Number(digits[index]),
        0,
      ) % 11;
    return checksum !== 10 && checksum === Number(digits[9])
      ? null
      : 'Nieprawidłowy numer NIP.';
  },
  REGON(value) {
    const digits = value.replace(/[\s-]/g, '');
    if (/^\d{9}$/.test(digits)) {
      const checksum = [8, 9, 2, 3, 4, 5, 6, 7].reduce(
        (sum, weight, index) => sum + weight * Number(digits[index]),
        0,
      );
      return (checksum % 11) % 10 === Number(digits[8])
        ? null
        : 'Nieprawidłowy numer REGON.';
    }
    if (/^\d{14}$/.test(digits)) {
      const checksum = [2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8].reduce(
        (sum, weight, index) => sum + weight * Number(digits[index]),
        0,
      );
      return (checksum % 11) % 10 === Number(digits[13])
        ? null
        : 'Nieprawidłowy numer REGON.';
    }
    return 'REGON ma 9 albo 14 cyfr.';
  },
  ZIP_CODE: (value) =>
    /^\d{2}-\d{3}$/.test(value.trim())
      ? null
      : 'Wpisz kod pocztowy w formacie 00-000.',
  EMAIL: (value) =>
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())
      ? null
      : 'Wpisz poprawny adres e-mail.',
  SERIAL_NUMBER_ID_CARD: (value) =>
    /^[A-Z]{3}\d{6}$/i.test(value.replace(/[\s-]/g, ''))
      ? null
      : 'Wpisz serię i numer dowodu, np. ABC123456.',
  ADE: (value) =>
    /^AE:PL-\d{5}-\d{5}-[A-Z]{5}-\d{2}$/i.test(value.trim())
      ? null
      : 'Wpisz adres do e-Doręczeń, np. AE:PL-12345-67890-ABCDE-12.',
};

export function getFieldRules(field: FormField): string[] {
  return Array.isArray(field.validation) ? field.validation : [];
}

export function isInputField(field: FormField): boolean {
  return inputFieldTypes.has(field.type);
}

export function validateField(field: FormField, value: unknown): string | null {
  const rules = getFieldRules(field);
  const empty =
    value === undefined ||
    value === null ||
    value === '' ||
    (Array.isArray(value) && value.length === 0);

  if (field.type === 'CONSENT_SECTION') {
    const consents = field.consentSectionConfig?.consents ?? [];
    return consents.some(
      (consent, index) =>
        consent.required && (!Array.isArray(value) || !value[index]),
    )
      ? 'Zaznacz wymagane zgody.'
      : null;
  }
  if (empty) return rules.includes('REQUIRED') ? 'To pole jest wymagane.' : null;

  for (const rule of rules) {
    const validate = validators[rule];
    const error = validate && typeof value === 'string' ? validate(value) : null;
    if (error) return error;
  }

  return null;
}