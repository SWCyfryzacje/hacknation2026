"use client";

import { useActionState, useState } from "react";
import {
  login,
  signup,
  requestPasswordReset,
  type AuthState,
} from "./actions";
import { Field, FormMessage, SubmitButton } from "./fields";

type Mode = "login" | "signup" | "reset";

const initial: AuthState = {};

const titles: Record<Mode, { title: string; subtitle: string }> = {
  login: {
    title: "Zaloguj się",
    subtitle: "Dostęp do panelu zarządzania federacją, uprawnieniami i audytem.",
  },
  signup: {
    title: "Załóż konto",
    subtitle: "Po rejestracji wyślemy link potwierdzający na podany adres.",
  },
  reset: {
    title: "Nie pamiętasz hasła?",
    subtitle: "Podaj e-mail — wyślemy link do ustawienia nowego hasła.",
  },
};

export function LoginForm({ next }: { next: string }) {
  const [mode, setMode] = useState<Mode>("login");
  const { title, subtitle } = titles[mode];

  return (
    <>
      <h1 className="mt-8 text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-2 text-sm leading-relaxed text-muted">{subtitle}</p>

      {mode !== "reset" && (
        <div
          role="tablist"
          className="mt-8 grid grid-cols-2 rounded-lg border border-border-subtle bg-surface p-1 text-sm"
        >
          {(["login", "signup"] as const).map((m) => (
            <button
              key={m}
              type="button"
              role="tab"
              aria-selected={mode === m}
              onClick={() => setMode(m)}
              className={`rounded-md px-3 py-1.5 transition-colors ${
                mode === m
                  ? "bg-background font-medium shadow-sm"
                  : "text-muted hover:text-foreground"
              }`}
            >
              {m === "login" ? "Logowanie" : "Rejestracja"}
            </button>
          ))}
        </div>
      )}

      {/* key wymusza świeży stan formularza przy zmianie trybu */}
      {mode === "login" && (
        <LoginFields key="login" next={next} onForgot={() => setMode("reset")} />
      )}
      {mode === "signup" && <SignupFields key="signup" />}
      {mode === "reset" && (
        <ResetFields key="reset" onBack={() => setMode("login")} />
      )}
    </>
  );
}

function LoginFields({ next, onForgot }: { next: string; onForgot: () => void }) {
  const [state, action] = useActionState(login, initial);
  return (
    <form action={action} className="mt-6 flex flex-col gap-4">
      <input type="hidden" name="next" value={next} />
      <Field label="E-mail" type="email" name="email" autoComplete="email" />
      <div className="flex flex-col gap-1.5">
        <Field
          label="Hasło"
          type="password"
          name="password"
          autoComplete="current-password"
        />
        <button
          type="button"
          onClick={onForgot}
          className="self-end text-xs text-muted underline-offset-4 hover:text-foreground hover:underline"
        >
          Nie pamiętasz hasła?
        </button>
      </div>
      <FormMessage state={state} />
      <SubmitButton>Zaloguj</SubmitButton>
    </form>
  );
}

function SignupFields() {
  const [state, action] = useActionState(signup, initial);
  if (state.message) {
    return (
      <div className="mt-6">
        <FormMessage state={state} />
      </div>
    );
  }
  return (
    <form action={action} className="mt-6 flex flex-col gap-4">
      <Field label="E-mail" type="email" name="email" autoComplete="email" />
      <Field
        label="Hasło (min. 8 znaków)"
        type="password"
        name="password"
        minLength={8}
        autoComplete="new-password"
      />
      <Field
        label="Powtórz hasło"
        type="password"
        name="confirm"
        minLength={8}
        autoComplete="new-password"
      />
      <FormMessage state={state} />
      <SubmitButton>Załóż konto</SubmitButton>
    </form>
  );
}

function ResetFields({ onBack }: { onBack: () => void }) {
  const [state, action] = useActionState(requestPasswordReset, initial);
  return (
    <form action={action} className="mt-8 flex flex-col gap-4">
      {!state.message && (
        <Field label="E-mail" type="email" name="email" autoComplete="email" />
      )}
      <FormMessage state={state} />
      {!state.message && <SubmitButton>Wyślij link</SubmitButton>}
      <button
        type="button"
        onClick={onBack}
        className="text-sm text-muted underline-offset-4 hover:text-foreground hover:underline"
      >
        ← Wróć do logowania
      </button>
    </form>
  );
}
