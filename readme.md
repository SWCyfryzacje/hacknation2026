# MCPolska

Federacyjny gateway MCP — projekt na HackNation 2026. Kontekst i cele:
[project-context.md](project-context.md).

## Struktura

| Katalog | Co to |
| --- | --- |
| [web/](web/) | landing page (Next.js 16, Tailwind 4) → deploy na Vercel, domena `oazai.pl` |

Kolejne komponenty (gateway MCP, aplikacje demo) dochodzą osobno.

## Landing page lokalnie

```bash
cd web
npm install
npm run dev     # http://localhost:3000
```

Deploy i podłączenie domeny: [DEPLOY.md](DEPLOY.md).
