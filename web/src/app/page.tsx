const pillars = [
  {
    label: "01",
    title: "Federacja MCP",
    body: "Wiele niezależnych aplikacji, każda z własnym serwerem MCP, podłączonych przez jeden gateway. Rejestr serwerów, agregacja narzędzi, routing wywołań.",
  },
  {
    label: "02",
    title: "Uprawnienia",
    body: "Centralna kontrola dostępu na poziomie pojedynczego narzędzia. Jawne nadawanie i odbieranie, egzekwowanie po stronie serwera — nigdy klienta.",
  },
  {
    label: "03",
    title: "Audyt",
    body: "Każde wywołanie narzędzia zapisane: kto, z jakiej aplikacji, jakie narzędzie, jaka decyzja autoryzacyjna, jaki wynik.",
  },
];

const notThis = [
  "chatbot",
  "nowy model",
  "zamiennik aplikacji",
  "otwarte API dla wszystkiego",
];

export default function Home() {
  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b border-border-subtle">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-5">
          <span className="font-mono text-sm tracking-tight">
            MC<span className="text-accent">Polska</span>
          </span>
          <span className="font-mono text-xs text-muted">
            HackNation · proof of concept
          </span>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-6">
        <section className="py-20 sm:py-28">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">
            Model Context Protocol · infrastruktura
          </p>
          <h1 className="mt-5 text-4xl font-semibold leading-[1.1] tracking-tight sm:text-6xl">
            Jedno wejście dla AI obywateli
            <br />
            do wielu aplikacji i usług publicznych.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted">
            MCPolska to federacyjny gateway MCP — wspólna warstwa integracyjna,
            przez którą asystenci AI korzystają z niezależnie rozwijanych
            aplikacji. Bez pisania osobnej integracji dla każdej pary asystent ×
            usługa.
          </p>

          <div className="mt-10 flex flex-wrap items-center gap-3">
            <a
              href="#filary"
              className="rounded-full bg-foreground px-5 py-2.5 text-sm font-medium text-background transition-opacity hover:opacity-85"
            >
              Jak to działa
            </a>
            <span className="rounded-full border border-border-subtle px-5 py-2.5 font-mono text-sm text-muted">
              mcp.oazai.pl · wkrótce
            </span>
          </div>
        </section>

        <section className="rounded-2xl border border-border-subtle bg-surface p-6 sm:p-8">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">
            Przepływ
          </p>
          <div className="mt-5 flex flex-col gap-3 font-mono text-sm sm:flex-row sm:items-center">
            {[
              "Klient MCP",
              "MCPolska Gateway",
              "Serwer MCP",
              "Aplikacja",
            ].map((step, i) => (
              <div key={step} className="flex items-center gap-3">
                <span
                  className={
                    i === 1
                      ? "rounded-lg bg-foreground px-3 py-2 text-background"
                      : "rounded-lg border border-border-subtle px-3 py-2"
                  }
                >
                  {step}
                </span>
                {i < 3 && <span className="text-muted">→</span>}
              </div>
            ))}
          </div>
          <p className="mt-5 max-w-2xl text-sm leading-relaxed text-muted">
            Gateway odpowiada za uwierzytelnianie, uprawnienia, routing i audyt.
            Aplikacje zachowują własną logikę, dane i infrastrukturę — nie są
            przepisywane do gatewaya.
          </p>
        </section>

        <section id="filary" className="scroll-mt-16 py-20">
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            Trzy filary
          </h2>
          <div className="mt-8 grid gap-5 sm:grid-cols-3">
            {pillars.map((p) => (
              <article
                key={p.label}
                className="rounded-2xl border border-border-subtle p-6"
              >
                <span className="font-mono text-xs text-accent">{p.label}</span>
                <h3 className="mt-3 text-lg font-medium">{p.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">
                  {p.body}
                </p>
              </article>
            ))}
          </div>
        </section>

        <section className="border-t border-border-subtle py-20">
          <div className="grid gap-10 sm:grid-cols-2">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">
                AI Handoff
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-muted">
                Drugi filar projektu: kontrolowane przekazanie kontekstu zadania
                między asystentami AI. Nie cała historia rozmowy — strukturalne
                podsumowanie, podjęte decyzje, braki i następny krok.
              </p>
              <p className="mt-4 font-mono text-sm">
                Claude <span className="text-muted">→</span> MCPolska{" "}
                <span className="text-muted">→</span> inny asystent
              </p>
            </div>
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">
                Czym to nie jest
              </h2>
              <ul className="mt-4 flex flex-wrap gap-2">
                {notThis.map((item) => (
                  <li
                    key={item}
                    className="rounded-full border border-border-subtle px-3 py-1.5 font-mono text-xs text-muted line-through decoration-accent/70"
                  >
                    {item}
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-sm leading-relaxed text-muted">
                To infrastruktura: integracja, federacja, uprawnienia i audyt.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border-subtle">
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-2 px-6 py-8 font-mono text-xs text-muted sm:flex-row sm:items-center sm:justify-between">
          <span>MCPolska · oazai.pl</span>
          <span>Prototyp. Nie jest produkcyjną infrastrukturą krajową.</span>
        </div>
      </footer>
    </div>
  );
}
