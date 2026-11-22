export interface ProposedDictionary {
  name: string;
  description?: string;
  values: string[];
  used_by?: string[];
}

export interface ReportAnalysis {
  analyzer?: string;
  model?: string;
  authority?: string;
  llmUsage?: {
    calls?: number;
    prompt_tokens?: number;
    completion_tokens?: number;
  };
}

export interface ReportStats {
  pages?: number;
  sections?: number;
  fields?: number;
  conditional?: number;
}

export interface FormReport {
  analysis?: ReportAnalysis;
  stats?: ReportStats;
  durationMs?: number;
  extraction?: {
    ocr?: boolean;
    ocrEngine?: string;
  };
  issues?: string[];
  warnings?: string[];
  proposedDictionaries?: ProposedDictionary[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string');
}

function hasOptionalString(
  value: Record<string, unknown>,
  property: string,
): boolean {
  return value[property] === undefined || typeof value[property] === 'string';
}

function hasOptionalNumber(
  value: Record<string, unknown>,
  property: string,
): boolean {
  return value[property] === undefined || typeof value[property] === 'number';
}

function isReportAnalysis(value: unknown): value is ReportAnalysis {
  if (!isRecord(value)) return false;
  if (
    !hasOptionalString(value, 'analyzer') ||
    !hasOptionalString(value, 'model') ||
    !hasOptionalString(value, 'authority')
  ) {
    return false;
  }

  if (value.llmUsage === undefined) return true;
  return (
    isRecord(value.llmUsage) &&
    hasOptionalNumber(value.llmUsage, 'calls') &&
    hasOptionalNumber(value.llmUsage, 'prompt_tokens') &&
    hasOptionalNumber(value.llmUsage, 'completion_tokens')
  );
}

function isReportStats(value: unknown): value is ReportStats {
  return (
    isRecord(value) &&
    hasOptionalNumber(value, 'pages') &&
    hasOptionalNumber(value, 'sections') &&
    hasOptionalNumber(value, 'fields') &&
    hasOptionalNumber(value, 'conditional')
  );
}

function isReportExtraction(value: unknown): boolean {
  return (
    isRecord(value) &&
    (value.ocr === undefined || typeof value.ocr === 'boolean') &&
    hasOptionalString(value, 'ocrEngine')
  );
}

function isProposedDictionary(value: unknown): value is ProposedDictionary {
  return (
    isRecord(value) &&
    typeof value.name === 'string' &&
    (value.description === undefined || typeof value.description === 'string') &&
    isStringArray(value.values) &&
    (value.used_by === undefined || isStringArray(value.used_by))
  );
}

export function isFormReport(value: unknown): value is FormReport {
  if (!isRecord(value)) return false;

  return (
    (value.analysis === undefined || isReportAnalysis(value.analysis)) &&
    (value.stats === undefined || isReportStats(value.stats)) &&
    (value.durationMs === undefined || typeof value.durationMs === 'number') &&
    (value.extraction === undefined || isReportExtraction(value.extraction)) &&
    (value.issues === undefined || isStringArray(value.issues)) &&
    (value.warnings === undefined || isStringArray(value.warnings)) &&
    (value.proposedDictionaries === undefined ||
      (Array.isArray(value.proposedDictionaries) &&
        value.proposedDictionaries.every(isProposedDictionary)))
  );
}