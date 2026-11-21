"use client";

import { useFormStatus } from "react-dom";
import type { AuthState } from "./actions";

export function Field({
  label,
  ...props
}: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="font-mono text-xs uppercase tracking-wider text-muted">
        {label}
      </span>
      <input
        required
        {...props}
        className="rounded-lg border border-border-subtle bg-surface px-3 py-2.5 text-sm outline-none transition-colors focus:border-accent"
      />
    </label>
  );
}

export function SubmitButton({ children }: { children: React.ReactNode }) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="mt-2 rounded-lg bg-foreground px-4 py-2.5 text-sm font-medium text-background transition-opacity hover:opacity-85 disabled:opacity-50"
    >
      {pending ? "Chwileczkę…" : children}
    </button>
  );
}

export function FormMessage({ state }: { state: AuthState }) {
  if (state.error) {
    return (
      <p
        role="alert"
        className="rounded-lg border border-accent/40 px-3 py-2 text-sm text-accent"
      >
        {state.error}
      </p>
    );
  }
  if (state.message) {
    return (
      <p
        role="status"
        className="rounded-lg border border-border-subtle bg-surface px-3 py-2 text-sm text-muted"
      >
        {state.message}
      </p>
    );
  }
  return null;
}
