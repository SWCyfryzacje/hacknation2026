import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  clearWorkspace,
  readWorkspace,
  saveWorkspace,
  type WorkspaceState,
} from './workspaceStorage';

const STORAGE_KEY = 'formularze-workspace';
const values = new Map<string, string>();
const localStorageMock = {
  getItem: (key: string) => values.get(key) ?? null,
  setItem: (key: string, value: string) => values.set(key, value),
  removeItem: (key: string) => values.delete(key),
};

const workspace: WorkspaceState = {
  result: {
    form: { tabs: [] },
    report: null,
    sourceName: 'form.json',
  },
  activeStep: 'form',
  answers: { applicant: 'Jan Kowalski', accepted: true },
  pageIndex: 2,
  showTechNames: true,
  activeTab: 'preview',
};

beforeEach(() => {
  values.clear();
  vi.stubGlobal('localStorage', localStorageMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('workspace storage', () => {
  it('round-trips the form result and view state', () => {
    saveWorkspace(workspace);

    expect(readWorkspace()).toEqual(workspace);
    expect(JSON.parse(values.get(STORAGE_KEY) ?? '{}')).toMatchObject({
      version: 1,
      activeStep: 'form',
    });
  });

  it('returns null when no workspace has been saved', () => {
    expect(readWorkspace()).toBeNull();
  });

  it.each([
    '{invalid json',
    JSON.stringify({ version: 99, ...workspace }),
    JSON.stringify({ version: 1, activeStep: 'form' }),
  ])(
    'clears malformed or unsupported data',
    (stored) => {
      values.set(STORAGE_KEY, stored);

      expect(readWorkspace()).toBeNull();
      expect(values.has(STORAGE_KEY)).toBe(false);
    },
  );

  it('does not throw when reading or writing storage fails', () => {
    vi.stubGlobal('localStorage', {
      getItem: () => {
        throw new Error('blocked');
      },
      setItem: () => {
        throw new Error('quota exceeded');
      },
      removeItem: () => {
        throw new Error('blocked');
      },
    });

    expect(readWorkspace()).toBeNull();
    expect(() => saveWorkspace(workspace)).not.toThrow();
    expect(() => clearWorkspace()).not.toThrow();
  });

  it('removes a saved workspace', () => {
    saveWorkspace(workspace);
    clearWorkspace();

    expect(readWorkspace()).toBeNull();
  });

  it('replaces the previous workspace without persisting unrelated properties', () => {
    saveWorkspace(workspace);
    saveWorkspace(
      {
        ...workspace,
        result: { ...workspace.result, sourceName: 'new.json' },
        token: 'secret',
      } as WorkspaceState,
    );

    expect(readWorkspace()?.result.sourceName).toBe('new.json');
    expect(JSON.parse(values.get(STORAGE_KEY) ?? '{}')).not.toHaveProperty('token');
  });
});