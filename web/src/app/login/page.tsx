import Link from "next/link";
import { safeNext } from "@/lib/safe-next";
import { LoginForm } from "./login-form";

const errors: Record<string, string> = {
  invalid_link: "Link jest nieprawidłowy.",
  expired_link: "Link wygasł lub został już użyty. Spróbuj ponownie.",
  session_required: "Sesja wygasła. Wyślij link do zmiany hasła jeszcze raz.",
};

export default async function LoginPage({
  searchParams,
}: PageProps<"/login">) {
  const params = await searchParams;
  const next = safeNext(params.next);
  const error = typeof params.error === "string" ? errors[params.error] : null;

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-6 py-20">
      <Link href="/" className="font-mono text-sm tracking-tight">
        MC<span className="text-accent">Polska</span>
      </Link>

      {error && (
        <p
          role="alert"
          className="mt-6 rounded-lg border border-accent/40 px-3 py-2 text-sm text-accent"
        >
          {error}
        </p>
      )}

      <LoginForm next={next} />
    </main>
  );
}
