import { isFormConfiguration, type FormResult } from '@/types/form';
import { isFormReport } from '@/types/report';

const STORAGE_KEY = 'formularze-workspace';
const STORAGE_VERSION = 1;

export type WorkspaceStep = 'upload' | 'form';
export type WorkspaceTab = 'preview' | 'report' | 'json';

export interface WorkspaceState {
  result: FormResult;
  activeStep: WorkspaceStep;
  answers: Record<string, unknown>;
  pageIndex: number;
  showTechNames: boolean;
  activeTab: WorkspaceTab;
}

interface StoredWorkspace extends WorkspaceState {
  version: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isJsonValue(value: unknown, seen = new WeakSet<object>()): boolean {
  if (
    value === null ||
    typeof value === 'string' ||
    typeof value === 'boolean' ||
    (typeof value === 'number' && Number.isFinite(value))
  ) {
    return true;
  }
  if (typeof value !== 'object') return false;
  if (seen.has(value)) return false;
  seen.add(value);

  if (Array.isArray(value)) return value.every((item) => isJsonValue(item, seen));
  const prototype = Object.getPrototypeOf(value);
  return (
    (prototype === Object.prototype || prototype === null) &&
    Object.values(value).every((item) => isJsonValue(item, seen))
  );
}

function isWorkspaceState(value: unknown): value is WorkspaceState {
  if (!isRecord(value) || !isRecord(value.result)) return false;

  const result = value.result;
  return (
    isFormConfiguration(result.form) &&
    (result.report === null || isFormReport(result.report)) &&
    typeof result.sourceName === 'string' &&
    (value.activeStep === 'upload' || value.activeStep === 'form') &&
    isRecord(value.answers) &&
    isJsonValue(value.answers) &&
    Number.isInteger(value.pageIndex) &&
    (value.pageIndex as number) >= 0 &&
    typeof value.showTechNames === 'boolean' &&
    (value.activeTab === 'preview' ||
      value.activeTab === 'report' ||
      value.activeTab === 'json')
  );
}

export function readWorkspace(): WorkspaceState | null {
  try {
    const stored = globalThis.localStorage.getItem(STORAGE_KEY);
    if (stored === null) return null;

    const parsed: unknown = JSON.parse(stored);
    if (
      !isRecord(parsed) ||
      parsed.version !== STORAGE_VERSION ||
      !isWorkspaceState(parsed)
    ) {
      globalThis.localStorage.removeItem(STORAGE_KEY);
      return null;
    }

    return {
      result: parsed.result,
      activeStep: parsed.activeStep,
      answers: parsed.answers,
      pageIndex: parsed.pageIndex,
      showTechNames: parsed.showTechNames,
      activeTab: parsed.activeTab,
    };
  } catch {
    try {
      globalThis.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Storage can be unavailable; there is nothing else to recover here.
    }
    return null;
  }
}

export function saveWorkspace(workspace: WorkspaceState): void {
  try {
    if (!isWorkspaceState(workspace)) return;
    const stored: StoredWorkspace = {
      version: STORAGE_VERSION,
      result: workspace.result,
      activeStep: workspace.activeStep,
      answers: workspace.answers,
      pageIndex: workspace.pageIndex,
      showTechNames: workspace.showTechNames,
      activeTab: workspace.activeTab,
    };
    globalThis.localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
  } catch {
    // Storage can be unavailable or full; the in-memory application state remains usable.
  }
}

export function clearWorkspace(): void {
  try {
    globalThis.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Storage can be unavailable; logout should still complete.
  }
}