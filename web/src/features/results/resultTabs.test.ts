import { describe, expect, it } from 'vitest';
import { ENABLE_JSON_DEBUG_VIEW } from '@/config/featureFlags';
import { isFormReport } from '@/types/report';
import { getResultTabs } from './resultTabs';

describe('result tab visibility', () => {
  it('shows JSON navigation by default', () => {
    expect(ENABLE_JSON_DEBUG_VIEW).toBe(true);
    expect(getResultTabs(true, ENABLE_JSON_DEBUG_VIEW).map((tab) => tab.id)).toEqual([
      'preview',
      'report',
      'json',
    ]);
  });

  it('offers the JSON tab only when debug mode is enabled', () => {
    expect(getResultTabs(true, true).map((tab) => tab.id)).toEqual([
      'preview',
      'report',
      'json',
    ]);
  });

  it('hides report navigation when no report exists', () => {
    expect(getResultTabs(false, false).map((tab) => tab.id)).toEqual([
      'preview',
    ]);
  });
});

describe('report payload validation', () => {
  it('accepts supported stats, usage, issues, and dictionary data', () => {
    expect(
      isFormReport({
        analysis: {
          analyzer: 'llm',
          model: 'test-model',
          llmUsage: { calls: 1, prompt_tokens: 100, completion_tokens: 50 },
        },
        stats: { pages: 4, sections: 5, fields: 12, conditional: 2 },
        durationMs: 1200,
        extraction: { ocr: true, ocrEngine: 'sample-ocr' },
        issues: [],
        warnings: ['Review the mapped field.'],
        proposedDictionaries: [
          {
            name: 'Sample',
            description: 'Values for the sample field.',
            values: ['One', 'Two'],
            used_by: ['sample_field'],
          },
        ],
      }),
    ).toBe(true);
  });

  it('rejects malformed report statistics and dictionary values', () => {
    expect(isFormReport({ stats: { pages: 'four' } })).toBe(false);
    expect(
      isFormReport({
        proposedDictionaries: [{ name: 'Invalid', values: [1, 2] }],
      }),
    ).toBe(false);
    expect(isFormReport(null)).toBe(false);
  });
});