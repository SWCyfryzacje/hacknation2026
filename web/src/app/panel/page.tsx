import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { signout } from "../login/actions";

export default async function PanelPage() {
  const supabase = await createClient();

  // Nie polegaj wyłącznie na proxy.ts — autoryzację sprawdzaj też tutaj.
  // getUser() weryfikuje token u Supabase, w przeciwieństwie do getSession().
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login?next=/panel");

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-16">
      <div className="flex items-center justify-between">
        <Link href="/" className="font-mono text-sm tracking-tight">
          MC<span className="text-accent">Polska</span>
        </Link>
        <form action={signout}>
          <button
            type="submit"
            className="rounded-full border border-border-subtle px-4 py-1.5 font-mono text-xs text-muted transition-opacity hover:opacity-70"
          >
            Wyloguj
          </button>
        </form>
      </div>

      <h1 className="mt-10 text-3xl font-semibold tracking-tight">Panel</h1>
      <p className="mt-2 text-sm text-muted">
        Zalogowany jako <span className="text-foreground">{user.email}</span>
      </p>

      <dl className="mt-8 grid gap-px overflow-hidden rounded-2xl border border-border-subtle bg-border-subtle sm:grid-cols-2">
        {[
          ["user id", user.id],
          ["dostawca", user.app_metadata.provider ?? "—"],
          [
            "e-mail potwierdzony",
            user.email_confirmed_at ? "tak" : "nie",
          ],
          [
            "konto utworzone",
            new Date(user.created_at).toLocaleString("pl-PL"),
          ],
        ].map(([k, v]) => (
          <div key={k} className="bg-background p-5">
            <dt className="font-mono text-xs uppercase tracking-wider text-muted">
              {k}
            </dt>
            <dd className="mt-1.5 break-all font-mono text-sm">{v}</dd>
          </div>
        ))}
      </dl>

      <p className="mt-8 text-sm leading-relaxed text-muted">
        Tu trafi rejestr serwerów MCP, nadawanie uprawnień i podgląd audit logu.
      </p>
    </main>
  );
}
