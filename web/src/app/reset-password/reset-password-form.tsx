"use client";

import { useActionState } from "react";
import { updatePassword, type AuthState } from "../login/actions";
import { Field, FormMessage, SubmitButton } from "../login/fields";

const initial: AuthState = {};

export function ResetPasswordForm() {
  const [state, action] = useActionState(updatePassword, initial);
  return (
    <form action={action} className="mt-8 flex flex-col gap-4">
      <Field
        label="Nowe hasło (min. 8 znaków)"
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
      <SubmitButton>Zapisz hasło</SubmitButton>
    </form>
  );
}
