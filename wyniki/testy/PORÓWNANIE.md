# Porównanie modeli — testy REST API

Wygenerowano: 2026-11-22T02:17:03+00:00 z `wyniki/testy/rejestr.json` (`backend/scripts/summary_tests.py`).

Każda para plik × model przetworzona raz (rejestr bez duplikatów). „OK” = wynik modelu językowego; pozostałe to analiza regułowa po błędzie modelu (`fallback`) lub błąd żądania. Koszt = tokeny × ceny z publicznego katalogu Eden AI (bez OCR).

| Model | Zestaw | OK / wszystkie | Skuteczność | Czas klienta śr. / mediana [s] | Czas serwera śr. [s] | Pola śr. | Tokeny we + wy | Koszt szac. |
|---|---|---|---|---|---|---|---|---|
| `databricks/databricks-gpt-oss-120b@eu` | BIP (B1–B3) | 9 / 9 | 100% | 13.6 / 13.1 | 13.6 | 54 | 30 589 + 23 082 | $0.02 |
| `databricks/databricks-gpt-oss-120b@eu` | materiały wyzwania | 67 / 68 | 99% | 18.1 / 14.8 | 17.9 | 61 | 289 816 + 172 106 | $0.15 |
| `databricks/databricks-gpt-oss-120b@eu` | wygenerowane (T1–T8) | 48 / 48 | 100% | 9.8 / 8.8 | 9.8 | 46 | 134 077 + 80 274 | $0.07 |
| `google/gemma-4-31b-it` | BIP (B1–B3) | 9 / 9 | 100% | 17.3 / 11.6 | 17.3 | 54 | 29 523 + 8 535 | $0.00 |
| `google/gemma-4-31b-it` | materiały wyzwania | 65 / 68 | 96% | 53.6 / 52.1 | 53.5 | 58 | 283 071 + 119 933 | $0.00 |
| `google/gemma-4-31b-it` | wygenerowane (T1–T8) | 48 / 48 | 100% | 19.8 / 5.6 | 19.8 | 49 | 143 095 + 37 910 | $0.00 |
| `mistral/mistral-large-4-0@eu` | materiały wyzwania | 59 / 59 | 100% | 99.5 / 98.0 | 98.8 | 59 | 274 914 + 445 417 | $1.24 |
| `mistral/mistral-medium-3.5@eu` | BIP (B1–B3) | 7 / 9 | 78% | 9.0 / 8.7 | 8.9 | 60 | 25 310 + 7 844 | $0.11 |
| `mistral/mistral-medium-3.5@eu` | materiały wyzwania | 66 / 68 | 97% | 12.0 / 7.5 | 11.9 | 61 | 437 166 + 80 910 | $1.39 |
| `mistral/mistral-medium-3.5@eu` | wygenerowane (T1–T8) | 48 / 48 | 100% | 3.9 / 3.2 | 3.8 | 48 | 134 423 + 17 946 | $0.37 |

Razem: 434 konwersji, fallback: 5, błędy: 3, szacowany koszt modeli: $3.34.
