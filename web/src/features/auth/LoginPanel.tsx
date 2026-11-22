import { useState, type FormEvent } from 'react';
import { getReadableError, requestAuthToken } from '@/services/api';

interface LoginPanelProps {
  authConfigError: string | null;
  loginConfigured: boolean;
  onLoginSuccess: (token: string) => void;
  sessionMessage: string | null;
}

export function LoginPanel({
  authConfigError,
  loginConfigured,
  onLoginSuccess,
  sessionMessage,
}: LoginPanelProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedUsername = username.trim();

    if (!normalizedUsername || !password) {
      setMessage('Podaj login i hasło.');
      return;
    }

    setIsSubmitting(true);
    setMessage(null);

    try {
      const token = await requestAuthToken(normalizedUsername, password);
      setPassword('');
      onLoginSuccess(token);
    } catch (error: unknown) {
      setMessage(getReadableError(error, 'Nie można połączyć się z serwerem.'));
    } finally {
      setIsSubmitting(false);
    }
  }

  const visibleMessage = message ?? authConfigError;

  return (
    <section className='w-full max-w-md self-center rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8'>
      <h2 className='text-xl font-semibold'>Zaloguj się</h2>
      <p className='mt-2 text-sm text-slate-600'>
        Zaloguj się, aby rozpocząć przetwarzanie dokumentu.
      </p>

      {!loginConfigured && !authConfigError && (
        <p className='mt-5 rounded-lg bg-amber-50 p-3 text-sm text-amber-900'>
          Logowanie nie jest skonfigurowane na serwerze (AUTH_USERNAME,
          AUTH_PASSWORD).
        </p>
      )}

      {sessionMessage && (
        <p aria-live='polite' className='mt-5 text-sm text-red-700' role='alert'>
          {sessionMessage}
        </p>
      )}

      <form className='mt-6 space-y-4' onSubmit={handleSubmit}>
        <div>
          <label className='mb-1.5 block text-sm font-medium' htmlFor='username'>
            Login
          </label>
          <input
            autoComplete='username'
            className='w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100'
            id='username'
            onChange={(event) => setUsername(event.target.value)}
            required
            value={username}
          />
        </div>
        <div>
          <label className='mb-1.5 block text-sm font-medium' htmlFor='password'>
            Hasło
          </label>
          <input
            autoComplete='current-password'
            className='w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100'
            id='password'
            onChange={(event) => setPassword(event.target.value)}
            required
            type='password'
            value={password}
          />
        </div>

        {visibleMessage && (
          <p aria-live='polite' className='text-sm text-red-700' role='alert'>
            {visibleMessage}
          </p>
        )}

        <button
          className='w-full rounded-lg bg-blue-700 px-4 py-3 font-semibold text-white hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 disabled:cursor-not-allowed disabled:opacity-60'
          disabled={isSubmitting}
          type='submit'
        >
          {isSubmitting ? 'Logowanie…' : 'Zaloguj się'}
        </button>
      </form>
    </section>
  );
}