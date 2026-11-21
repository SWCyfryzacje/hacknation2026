"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { headers } from "next/headers";
import { createClient } from "@/lib/supabase/server";
import { safeNext } from "@/lib/safe-next";

export type AuthState = { error?: string; message?: string };

const MIN_PASSWORD = 8;

function readCredentials(formData: FormData) {
  return {
    email: String(formData.get("email") ?? "").trim(),
    password: String(formData.get("password") ?? ""),
  };
}

/** Adres strony (np. http://localhost:3000) — do linków w mailach. */
async function getOrigin() {
  const h = await headers();
  const origin = h.get("origin");
  if (origin) return origin;
  const proto = h.get("x-forwarded-proto") ?? "http";
  return `${proto}://${h.get("x-forwarded-host") ?? h.get("host")}`;
}

function translate(message: string): string {
  const map: Record<string, string> = {
    "Invalid login credentials": "Nieprawidłowy e-mail lub hasło.",
    "Email not confirmed": "E-mail nie został potwierdzony. Sprawdź skrzynkę.",
    "User already registered": "Konto z tym adresem już istnieje.",
    "New password should be different from the old password.":
      "Nowe hasło musi różnić się od poprzedniego.",
  };
  if (map[message]) return map[message];
  if (/rate limit/i.test(message)) return "Zbyt wiele prób. Spróbuj za chwilę.";
  return message;
}

export async function login(
  _prev: AuthState,
  formData: FormData,
): Promise<AuthState> {
  const { email, password } = readCredentials(formData);
  if (!email || !password) return { error: "Podaj e-mail i hasło." };

  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) return { error: translate(error.message) };

  revalidatePath("/", "layout");
  redirect(safeNext(formData.get("next")));
}

export async function signup(
  _prev: AuthState,
  formData: FormData,
): Promise<AuthState> {
  const { email, password } = readCredentials(formData);
  const confirm = String(formData.get("confirm") ?? "");
  if (!email || !password) return { error: "Podaj e-mail i hasło." };
  if (password.length < MIN_PASSWORD) {
    return { error: `Hasło musi mieć min. ${MIN_PASSWORD} znaków.` };
  }
  if (password !== confirm) return { error: "Hasła nie są takie same." };

  const supabase = await createClient();
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: { emailRedirectTo: `${await getOrigin()}/auth/confirm` },
  });
  if (error) return { error: translate(error.message) };

  // Gdy w Supabase wyłączone jest potwierdzanie maila, sesja powstaje od razu.
  if (data.session) {
    revalidatePath("/", "layout");
    redirect("/panel");
  }

  return {
    message: `Konto założone. Sprawdź skrzynkę ${email} i kliknij link potwierdzający.`,
  };
}

export async function requestPasswordReset(
  _prev: AuthState,
  formData: FormData,
): Promise<AuthState> {
  const email = String(formData.get("email") ?? "").trim();
  if (!email) return { error: "Podaj e-mail." };

  const supabase = await createClient();
  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${await getOrigin()}/auth/confirm?next=/reset-password`,
  });
  if (error) return { error: translate(error.message) };

  // Ten sam komunikat niezależnie od tego, czy konto istnieje — nie zdradzamy tego.
  return {
    message: `Jeśli konto ${email} istnieje, wysłaliśmy link do ustawienia nowego hasła.`,
  };
}

export async function updatePassword(
  _prev: AuthState,
  formData: FormData,
): Promise<AuthState> {
  const password = String(formData.get("password") ?? "");
  const confirm = String(formData.get("confirm") ?? "");
  if (password.length < MIN_PASSWORD) {
    return { error: `Hasło musi mieć min. ${MIN_PASSWORD} znaków.` };
  }
  if (password !== confirm) return { error: "Hasła nie są takie same." };

  const supabase = await createClient();
  const { error } = await supabase.auth.updateUser({ password });
  if (error) return { error: translate(error.message) };

  revalidatePath("/", "layout");
  redirect("/panel");
}

export async function signout() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  revalidatePath("/", "layout");
  redirect("/login");
}
