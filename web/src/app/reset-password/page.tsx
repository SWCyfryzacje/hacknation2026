import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { ResetPasswordForm } from "./reset-password-form";

export default async function ResetPasswordPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Na tę stronę trafia się z linku w mailu, który tworzy sesję.
  if (!user) redirect("/login?error=session_required");

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-6 py-20">
      <Link href="/" className="font-mono text-sm tracking-tight">
        MC<span className="text-accent">Polska</span>
      </Link>
      <h1 className="mt-8 text-2xl font-semibold tracking-tight">
        Ustaw nowe hasło
      </h1>
      <p className="mt-2 text-sm leading-relaxed text-muted">
        Dla konta <span className="text-foreground">{user.email}</span>
      </p>
      <ResetPasswordForm />
    </main>
  );
}
