const TOKEN_KEY = 'formularze-token';

export interface AuthConfig {
  authEnabled: boolean;
  loginConfigured: boolean;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function getReadableError(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return fallback;
  return error instanceof Error ? error.message : fallback;
}

export function getSessionToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setSessionToken(token: string): void {
  try {
    sessionStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Session storage may be unavailable in restricted browser contexts.
  }
}

export function clearSessionToken(): void {
  try {
    sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // Session storage may be unavailable in restricted browser contexts.
  }
}

export async function getApiErrorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();

    if (typeof body === 'object' && body !== null && 'detail' in body) {
      const { detail } = body;
      if (typeof detail === 'string') return detail;
      if (Array.isArray(detail)) {
        return detail
          .map((item: unknown) => {
            if (typeof item === 'object' && item !== null && 'msg' in item) {
              return String(item.msg);
            }
            return '';
          })
          .filter(Boolean)
          .join('; ');
      }
    }
  } catch {
    // Non-JSON responses use the HTTP status fallback below.
  }

  return `Błąd HTTP ${response.status}`;
}

export async function fetchAuthConfig(): Promise<AuthConfig> {
  const response = await fetch('/api/v1/auth/config');
  if (!response.ok) {
    throw new ApiError(await getApiErrorMessage(response), response.status);
  }

  let config: unknown;
  try {
    config = await response.json();
  } catch {
    throw new Error('Nieprawidłowa odpowiedź konfiguracji logowania.');
  }
  if (
    typeof config !== 'object' ||
    config === null ||
    !('authEnabled' in config) ||
    typeof config.authEnabled !== 'boolean' ||
    !('loginConfigured' in config) ||
    typeof config.loginConfigured !== 'boolean'
  ) {
    throw new Error('Nieprawidłowa odpowiedź konfiguracji logowania.');
  }

  return {
    authEnabled: config.authEnabled,
    loginConfigured: config.loginConfigured,
  };
}

export async function requestAuthToken(
  username: string,
  password: string,
): Promise<string> {
  const response = await fetch('/api/v1/auth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    throw new ApiError(await getApiErrorMessage(response), response.status);
  }

  let result: unknown;
  try {
    result = await response.json();
  } catch {
    throw new Error('Serwer nie zwrócił prawidłowego tokenu logowania.');
  }
  if (
    typeof result !== 'object' ||
    result === null ||
    !('access_token' in result) ||
    typeof result.access_token !== 'string' ||
    result.access_token.length === 0
  ) {
    throw new Error('Serwer nie zwrócił prawidłowego tokenu logowania.');
  }

  return result.access_token;
}

export async function convertDocument(
  file: File,
  authRequired: boolean,
  token: string | null,
): Promise<unknown> {
  const body = new FormData();
  body.append('file', file);

  const headers: Record<string, string> = {};
  if (authRequired && token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch('/api/v1/forms/convert?report=true', {
    method: 'POST',
    headers,
    body,
  });

  if (!response.ok) {
    throw new ApiError(await getApiErrorMessage(response), response.status);
  }

  try {
    return await response.json();
  } catch {
    throw new Error('Serwer zwrócił nieprawidłową odpowiedź.');
  }
}