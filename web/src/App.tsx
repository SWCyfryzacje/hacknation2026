import { useEffect, useState } from 'react';
import { LoginPanel } from '@/features/auth/LoginPanel';
import { UploadPanel } from '@/features/upload/UploadPanel';
import { WorkflowSteps } from '@/components/WorkflowSteps';
import { ResultPanel } from '@/features/results/ResultPanel';
import {
  clearSessionToken,
  fetchAuthConfig,
  getSessionToken,
  getReadableError,
  setSessionToken,
  type AuthConfig,
} from '@/services/api';
import type { FormResult } from '@/types/form';

function App() {
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null);
  const [authConfigError, setAuthConfigError] = useState<string | null>(null);
  const [isLoadingAuthConfig, setIsLoadingAuthConfig] = useState(true);
  const [token, setToken] = useState(getSessionToken);
  const [sessionMessage, setSessionMessage] = useState<string | null>(null);
  const [activeStep, setActiveStep] = useState<'upload' | 'form'>('upload');
  const [formResult, setFormResult] = useState<FormResult | null>(null);

  useEffect(() => {
    let isMounted = true;

    fetchAuthConfig()
      .then((config) => {
        if (isMounted) {
          setAuthConfig(config);
          setAuthConfigError(null);
        }
      })
      .catch((error: unknown) => {
        if (isMounted) {
          setAuthConfigError(
            getReadableError(error, 'Nie można połączyć się z serwerem.'),
          );
        }
      })
      .finally(() => {
        if (isMounted) setIsLoadingAuthConfig(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const isAuthenticated = authConfig?.authEnabled === false || Boolean(token);

  function handleLoginSuccess(accessToken: string) {
    setSessionToken(accessToken);
    setToken(accessToken);
    setSessionMessage(null);
  }

  function handleLogout() {
    clearSessionToken();
    setToken(null);
    setFormResult(null);
    setActiveStep('upload');
  }

  function handleSessionExpired() {
    clearSessionToken();
    setToken(null);
    setSessionMessage('Sesja wygasła — zaloguj się ponownie.');
  }

  function handleFormReady(result: FormResult) {
    setFormResult(result);
    setActiveStep('form');
  }

  return (
    <main className='min-h-full bg-slate-50 px-4 py-8 text-slate-900 sm:px-6 sm:py-12'>
      <div className='mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-5xl flex-col'>
        <header className='mb-10 flex items-center justify-between gap-4'>
          <div>
            <p className='text-sm font-semibold tracking-wide text-blue-700'>
              FORMULARZE
            </p>
            <h1 className='mt-1 text-2xl font-bold sm:text-3xl'>
              Przetwarzanie dokumentów
            </h1>
          </div>
          {isAuthenticated && authConfig?.authEnabled !== false && (
            <button
              className='rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold hover:bg-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700'
              onClick={handleLogout}
              type='button'
            >
              Wyloguj
            </button>
          )}
        </header>

        {isLoadingAuthConfig ? (
          <p aria-live='polite' className='text-slate-600'>
            Łączenie z serwerem…
          </p>
        ) : isAuthenticated ? (
          <>
            <WorkflowSteps activeStep={activeStep} />
            {activeStep === 'upload' ? (
              <UploadPanel
                authRequired={authConfig?.authEnabled ?? true}
                onFormReady={handleFormReady}
                onSessionExpired={handleSessionExpired}
                token={token}
              />
            ) : formResult ? (
              <ResultPanel
                onBackToUpload={() => setActiveStep('upload')}
                result={formResult}
              />
            ) : (
              <p className='text-slate-600'>Formularz nie jest dostępny.</p>
            )}
          </>
        ) : (
          <LoginPanel
            authConfigError={authConfigError}
            loginConfigured={authConfig?.loginConfigured ?? true}
            onLoginSuccess={handleLoginSuccess}
            sessionMessage={sessionMessage}
          />
        )}
      </div>
    </main>
  );
}

export default App;
