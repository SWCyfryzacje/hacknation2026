import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ApiError,
  clearSessionToken,
  convertDocument,
  fetchAuthConfig,
  getSessionToken,
  requestAuthToken,
  setSessionToken,
} from './api';

const fetchMock = vi.fn<
  (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
>();
const sessionValues = new Map<string, string>();
const sessionStorageMock = {
  getItem: (key: string) => sessionValues.get(key) ?? null,
  setItem: (key: string, value: string) => sessionValues.set(key, value),
  removeItem: (key: string) => sessionValues.delete(key),
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

beforeEach(() => {
  fetchMock.mockReset();
  sessionValues.clear();
  vi.stubGlobal('fetch', fetchMock);
  vi.stubGlobal('sessionStorage', sessionStorageMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('authentication API', () => {
  it('loads the auth configuration', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ authEnabled: true, loginConfigured: true }),
    );

    await expect(fetchAuthConfig()).resolves.toEqual({
      authEnabled: true,
      loginConfigured: true,
    });
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/auth/config');
  });

  it('preserves readable error details and status for failed login requests', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'Nieprawidłowe dane.' }, 401));

    await expect(requestAuthToken('worker', 'wrong')).rejects.toMatchObject({
      message: 'Nieprawidłowe dane.',
      status: 401,
    });
  });

  it('sends credentials and returns the access token', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ access_token: 'session-token' }));

    await expect(requestAuthToken('worker', 'secret')).resolves.toBe(
      'session-token',
    );
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'worker', password: 'secret' }),
    });
  });

  it('persists and clears the bearer token for the current browser session', () => {
    setSessionToken('session-token');
    expect(getSessionToken()).toBe('session-token');
    clearSessionToken();
    expect(getSessionToken()).toBeNull();
  });
});

describe('document conversion API', () => {
  it('sends multipart data and the bearer token when authentication is required', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ form: { tabs: [] }, report: null }));
    const file = new File(['document'], 'application.pdf', {
      type: 'application/pdf',
    });

    await convertDocument(file, true, 'session-token');

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/v1/forms/convert?report=true');
    expect(options?.method).toBe('POST');
    expect(options?.headers).toEqual({ Authorization: 'Bearer session-token' });
    expect((options?.body as FormData).get('file')).toMatchObject({
      name: 'application.pdf',
    });
  });

  it('omits bearer auth when authentication is disabled', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ form: { tabs: [] } }));
    const file = new File(['document'], 'application.pdf');

    await convertDocument(file, false, null);

    expect(fetchMock.mock.calls[0][1]?.headers).toEqual({});
  });

  it('identifies expired sessions from the conversion response', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'Expired' }, 401));
    const file = new File(['document'], 'application.pdf');

    await expect(convertDocument(file, true, 'expired-token')).rejects.toBeInstanceOf(
      ApiError,
    );
  });
});