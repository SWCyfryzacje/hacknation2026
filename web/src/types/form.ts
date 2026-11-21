import type { FormReport } from './report';

export interface FormOption {
  id?: string;
  name?: string;
  techName?: string;
}

export interface FormState {
  type: string;
  query?: string;
}

export interface FormConsent {
  description?: string;
  required?: boolean;
}

export interface FormField {
  id: string;
  type: string;
  techName: string;
  title?: string;
  description?: string;
  tooltipMessage?: string;
  dictionaryName?: string;
  options?: FormOption[];
  validation?: string[] | Record<string, unknown>;
  readOnly?: boolean;
  defaultValue?: unknown;
  defaultValueType?: string;
  repeatingSectionGrid?: FormGridItem[];
  states?: FormState[];
  consentSectionConfig?: { consents?: FormConsent[] };
  [key: string]: unknown;
}

export interface FormGridItem {
  x?: number;
  y?: number;
  field: FormField;
}

export interface FormQuestion extends FormGridItem {
  rows?: number;
  cols?: number;
}

export interface FormTab {
  id?: string;
  title?: string;
  type?: string;
  questions?: FormQuestion[];
}

export interface FormLink {
  source: string;
  target: string;
}

export interface FormConfiguration {
  title?: string;
  tabs: FormTab[];
  flow?: { links?: FormLink[] };
  [key: string]: unknown;
}

export interface FormResult {
  form: FormConfiguration;
  report: FormReport | null;
  sourceName: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isFormField(value: unknown): value is FormField {
  if (
    !isRecord(value) ||
    typeof value.id !== 'string' ||
    typeof value.type !== 'string' ||
    typeof value.techName !== 'string'
  ) {
    return false;
  }

  if (
    value.options !== undefined &&
    (!Array.isArray(value.options) ||
      !value.options.every(
        (option) =>
          isRecord(option) &&
          (option.id === undefined || typeof option.id === 'string') &&
          (option.name === undefined || typeof option.name === 'string'),
      ))
  ) {
    return false;
  }

  if (
    value.states !== undefined &&
    (!Array.isArray(value.states) ||
      !value.states.every(
        (state) =>
          isRecord(state) &&
          typeof state.type === 'string' &&
          (state.query === undefined || typeof state.query === 'string'),
      ))
  ) {
    return false;
  }

  return (
    (value.title === undefined || typeof value.title === 'string') &&
    (value.description === undefined || typeof value.description === 'string') &&
    (value.repeatingSectionGrid === undefined ||
      (Array.isArray(value.repeatingSectionGrid) &&
        value.repeatingSectionGrid.every(
          (item) => isRecord(item) && isFormField(item.field),
        )))
  );
}

function isFormQuestion(value: unknown): value is FormQuestion {
  return isRecord(value) && isFormField(value.field);
}

function isFormTab(value: unknown): value is FormTab {
  return (
    isRecord(value) &&
    (value.id === undefined || typeof value.id === 'string') &&
    (value.title === undefined || typeof value.title === 'string') &&
    (value.type === undefined || typeof value.type === 'string') &&
    (value.questions === undefined ||
      (Array.isArray(value.questions) && value.questions.every(isFormQuestion)))
  );
}

export function isFormConfiguration(value: unknown): value is FormConfiguration {
  return (
    isRecord(value) &&
    (value.title === undefined || typeof value.title === 'string') &&
    Array.isArray(value.tabs) &&
    value.tabs.every(isFormTab) &&
    (value.flow === undefined ||
      (isRecord(value.flow) &&
        (value.flow.links === undefined ||
          (Array.isArray(value.flow.links) &&
            value.flow.links.every(
              (link) =>
                isRecord(link) &&
                typeof link.source === 'string' &&
                typeof link.target === 'string',
            )))))
  );
}