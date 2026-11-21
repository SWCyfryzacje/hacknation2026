import { isFormConfiguration, type FormResult } from '@/types/form';
import { isFormReport } from '@/types/report';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export async function readFormFile(file: File): Promise<FormResult> {
  const contents = (await file.text()).replace(/^\uFEFF/, '');
  let parsed: unknown;
  try {
    parsed = JSON.parse(contents);
  } catch {
    throw new Error('Plik nie zawiera poprawnego JSON-u.');
  }
  const form =
    isRecord(parsed) && isFormConfiguration(parsed.form)
      ? parsed.form
      : parsed;

  if (!isFormConfiguration(form)) {
    throw new Error('Brak tablicy „tabs”.');
  }

  return {
    form,
    report:
      isRecord(parsed) && isFormReport(parsed.report) ? parsed.report : null,
    sourceName: file.name,
  };
}