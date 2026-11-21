import { describe, expect, it } from 'vitest';
import { readFormFile } from './formFile';

const form = { title: 'Sample form', tabs: [] };

describe('existing form JSON files', () => {
  it('loads a bare form configuration without making a conversion request', async () => {
    const file = new File([JSON.stringify(form)], 'existing.json');

    await expect(readFormFile(file)).resolves.toEqual({
      form,
      report: null,
      sourceName: 'existing.json',
    });
  });

  it('loads a wrapped form and valid report payload', async () => {
    const report = {
      issues: [],
      warnings: [],
      proposedDictionaries: [
        { name: 'Example', values: ['A', 'B'], used_by: ['field'] },
      ],
    };
    const file = new File([JSON.stringify({ form, report })], 'wrapped.json');

    await expect(readFormFile(file)).resolves.toEqual({
      form,
      report,
      sourceName: 'wrapped.json',
    });
  });

  it('rejects invalid JSON and configurations without tabs', async () => {
    await expect(
      readFormFile(new File(['not json'], 'broken.json')),
    ).rejects.toThrow('poprawnego JSON-u');
    await expect(
      readFormFile(new File(['{}'], 'missing-tabs.json')),
    ).rejects.toThrow('Brak tablicy');
  });
});