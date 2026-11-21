import { describe, expect, it } from 'vitest';
import {
  allowedDocumentExtensions,
  validateDocumentFile,
} from './fileValidation';

describe('document file validation', () => {
  it('accepts each supported extension without case sensitivity', () => {
    for (const extension of allowedDocumentExtensions) {
      expect(
        validateDocumentFile({
          name: `application${extension.toUpperCase()}`,
          size: 10,
        }),
      ).toBeNull();
    }
  });

  it('rejects unsupported extensions and missing extensions', () => {
    expect(validateDocumentFile({ name: 'application.txt', size: 10 })).toContain(
      'Nieobsługiwany format',
    );
    expect(validateDocumentFile({ name: 'application', size: 10 })).toContain(
      'brak rozszerzenia',
    );
  });

  it('rejects long names, forbidden characters, and empty files', () => {
    expect(
      validateDocumentFile({ name: `${'a'.repeat(247)}.pdf`, size: 10 }),
    ).toContain('250 znaków');
    expect(validateDocumentFile({ name: 'bad;name.pdf', size: 10 })).toContain(
      'niedozwolone znaki',
    );
    expect(validateDocumentFile({ name: 'empty.pdf', size: 0 })).toBe(
      'Plik jest pusty.',
    );
  });
});