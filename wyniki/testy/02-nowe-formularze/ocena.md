# Ocena względem klucza odpowiedzi (formularze wygenerowane T1–T8)

Generator: `backend/scripts/evaluate.py`. Klucz: `testy/formularze/T*.expected.json`. Oceniana jest część specyficzna dla wniosku; etykiety dopasowywane po podobieństwie. Tylko wyniki modelu językowego.

| Model | Plików | Kompletność pól | Precyzja pól | Typy (zgodne / dokładne) | Opcje wyboru | Zależności | Tytuł | Urząd | Wnioskodawca |
|---|---|---|---|---|---|---|---|---|---|
| gemma4 | 56 | 97% | 100% | 100% / 96% | 100% | 100% | 100% | 100% | 73% |
| gptoss | 56 | 98% | 86% | 99% / 94% | 96% | 95% | 100% | 100% | 98% |
| medium35 | 56 | 97% | 100% | 100% / 98% | 100% | 100% | 100% | 100% | 82% |

## Szczegóły (pliki)

| Model | Plik | Pola (znalezione / oczekiwane) | Kompletność | Precyzja | Zależności | Brakujące pola |
|---|---|---|---|---|---|---|
| gemma4 | T1.docx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| gemma4 | T1.ods.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| gemma4 | T1.pdf.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| gemma4 | T1.xlsx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| gemma4 | T1_skan.jpg.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| gemma4 | T1_skan.png.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| gemma4 | T1_word97.doc.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| gemma4 | T2.docx.json | 10 / 10 (wszystkich 10) | 100% | 100% | 1/1 | — |
| gemma4 | T2.ods.json | 10 / 10 (wszystkich 10) | 100% | 100% | 1/1 | — |
| gemma4 | T2.pdf.json | 8 / 10 (wszystkich 8) | 80% | 100% | 1/1 | Rysunek lub mapa określająca usytuowanie drzewa, Zgoda współwłaściciela nieruchomości (jeżeli dotyczy) |
| gemma4 | T2.xlsx.json | 10 / 10 (wszystkich 10) | 100% | 100% | 1/1 | — |
| gemma4 | T2_skan.jpg.json | 7 / 10 (wszystkich 8) | 70% | 88% | 1/1 | Planowany termin usunięcia, Rysunek lub mapa określająca usytuowanie drzewa, Zgoda współwłaściciela nieruchomości (jeżeli dotyczy) |
| gemma4 | T2_skan.png.json | 7 / 10 (wszystkich 8) | 70% | 88% | 1/1 | Planowany termin usunięcia, Rysunek lub mapa określająca usytuowanie drzewa, Zgoda współwłaściciela nieruchomości (jeżeli dotyczy) |
| gemma4 | T2_word97.doc.json | 10 / 10 (wszystkich 10) | 100% | 100% | 1/1 | — |
| gemma4 | T3.docx.json | 4 / 4 (wszystkich 4) | 100% | 100% | 0/0 | — |
| gemma4 | T3.ods.json | 4 / 4 (wszystkich 4) | 100% | 100% | 0/0 | — |
| gemma4 | T3.pdf.json | 4 / 4 (wszystkich 4) | 100% | 100% | 0/0 | — |
| gemma4 | T3.xlsx.json | 4 / 4 (wszystkich 4) | 100% | 100% | 0/0 | — |
| gemma4 | T3_skan.jpg.json | 3 / 4 (wszystkich 3) | 75% | 100% | 0/0 | Dowód uiszczenia opłaty skarbowej |
| gemma4 | T3_skan.png.json | 3 / 4 (wszystkich 3) | 75% | 100% | 0/0 | Dowód uiszczenia opłaty skarbowej |
| gemma4 | T3_word97.doc.json | 4 / 4 (wszystkich 4) | 100% | 100% | 0/0 | — |
| gemma4 | T4.docx.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| gemma4 | T4.ods.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| gemma4 | T4.pdf.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| gemma4 | T4.xlsx.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| gemma4 | T4_skan.jpg.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| gemma4 | T4_skan.png.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| gemma4 | T4_word97.doc.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| gemma4 | T5.docx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gemma4 | T5.ods.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gemma4 | T5.pdf.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gemma4 | T5.xlsx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gemma4 | T5_skan.jpg.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gemma4 | T5_skan.png.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gemma4 | T5_word97.doc.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gemma4 | T6.docx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gemma4 | T6.ods.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gemma4 | T6.pdf.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gemma4 | T6.xlsx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gemma4 | T6_skan.jpg.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gemma4 | T6_skan.png.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gemma4 | T6_word97.doc.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gemma4 | T7.docx.json | 8 / 8 (wszystkich 8) | 100% | 100% | 1/1 | — |
| gemma4 | T7.ods.json | 8 / 8 (wszystkich 8) | 100% | 100% | 1/1 | — |
| gemma4 | T7.pdf.json | 8 / 8 (wszystkich 8) | 100% | 100% | 1/1 | — |
| gemma4 | T7.xlsx.json | 8 / 8 (wszystkich 8) | 100% | 100% | 1/1 | — |
| gemma4 | T7_skan.jpg.json | 8 / 8 (wszystkich 8) | 100% | 100% | 1/1 | — |
| gemma4 | T7_skan.png.json | 8 / 8 (wszystkich 8) | 100% | 100% | 1/1 | — |
| gemma4 | T7_word97.doc.json | 8 / 8 (wszystkich 8) | 100% | 100% | 1/1 | — |
| gemma4 | T8.docx.json | 4 / 5 (wszystkich 4) | 80% | 100% | 1/1 | Faktury VAT stanowiące dowód zakupu oleju napędowego |
| gemma4 | T8.ods.json | 5 / 5 (wszystkich 5) | 100% | 100% | 1/1 | — |
| gemma4 | T8.pdf.json | 5 / 5 (wszystkich 5) | 100% | 100% | 1/1 | — |
| gemma4 | T8.xlsx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 1/1 | — |
| gemma4 | T8_skan.jpg.json | 5 / 5 (wszystkich 5) | 100% | 100% | 1/1 | — |
| gemma4 | T8_skan.png.json | 5 / 5 (wszystkich 5) | 100% | 100% | 1/1 | — |
| gemma4 | T8_word97.doc.json | 4 / 5 (wszystkich 4) | 80% | 100% | 1/1 | Faktury VAT stanowiące dowód zakupu oleju napędowego |
| gptoss | T1.docx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| gptoss | T1.ods.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| gptoss | T1.pdf.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| gptoss | T1.xlsx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| gptoss | T1_skan.jpg.json | 5 / 5 (wszystkich 8) | 100% | 62% | 2/2 | — |
| gptoss | T1_skan.png.json | 5 / 5 (wszystkich 8) | 100% | 62% | 0/2 | — |
| gptoss | T1_word97.doc.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| gptoss | T2.docx.json | 10 / 10 (wszystkich 10) | 100% | 100% | 1/1 | — |
| gptoss | T2.ods.json | 10 / 10 (wszystkich 10) | 100% | 100% | 1/1 | — |
| gptoss | T2.pdf.json | 10 / 10 (wszystkich 10) | 100% | 100% | 1/1 | — |
| gptoss | T2.xlsx.json | 10 / 10 (wszystkich 10) | 100% | 100% | 1/1 | — |
| gptoss | T2_skan.jpg.json | 7 / 10 (wszystkich 8) | 70% | 88% | 1/1 | Planowany termin usunięcia, Rysunek lub mapa określająca usytuowanie drzewa, Zgoda współwłaściciela nieruchomości (jeżeli dotyczy) |
| gptoss | T2_skan.png.json | 7 / 10 (wszystkich 8) | 70% | 88% | 1/1 | Planowany termin usunięcia, Rysunek lub mapa określająca usytuowanie drzewa, Zgoda współwłaściciela nieruchomości (jeżeli dotyczy) |
| gptoss | T2_word97.doc.json | 10 / 10 (wszystkich 10) | 100% | 100% | 1/1 | — |
| gptoss | T3.docx.json | 3 / 4 (wszystkich 8) | 75% | 38% | 0/0 | Dowód uiszczenia opłaty skarbowej |
| gptoss | T3.ods.json | 4 / 4 (wszystkich 9) | 100% | 44% | 0/0 | — |
| gptoss | T3.pdf.json | 4 / 4 (wszystkich 9) | 100% | 44% | 0/0 | — |
| gptoss | T3.xlsx.json | 4 / 4 (wszystkich 9) | 100% | 44% | 0/0 | — |
| gptoss | T3_skan.jpg.json | 3 / 4 (wszystkich 8) | 75% | 38% | 0/0 | Dowód uiszczenia opłaty skarbowej |
| gptoss | T3_skan.png.json | 3 / 4 (wszystkich 3) | 75% | 100% | 0/0 | Dowód uiszczenia opłaty skarbowej |
| gptoss | T3_word97.doc.json | 4 / 4 (wszystkich 9) | 100% | 44% | 0/0 | — |
| gptoss | T4.docx.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| gptoss | T4.ods.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| gptoss | T4.pdf.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| gptoss | T4.xlsx.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| gptoss | T4_skan.jpg.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| gptoss | T4_skan.png.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| gptoss | T4_word97.doc.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| gptoss | T5.docx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gptoss | T5.ods.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gptoss | T5.pdf.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gptoss | T5.xlsx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gptoss | T5_skan.jpg.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gptoss | T5_skan.png.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gptoss | T5_word97.doc.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gptoss | T6.docx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gptoss | T6.ods.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gptoss | T6.pdf.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gptoss | T6.xlsx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gptoss | T6_skan.jpg.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gptoss | T6_skan.png.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gptoss | T6_word97.doc.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| gptoss | T7.docx.json | 8 / 8 (wszystkich 11) | 100% | 73% | 1/1 | — |
| gptoss | T7.ods.json | 8 / 8 (wszystkich 11) | 100% | 73% | 1/1 | — |
| gptoss | T7.pdf.json | 8 / 8 (wszystkich 11) | 100% | 73% | 1/1 | — |
| gptoss | T7.xlsx.json | 8 / 8 (wszystkich 11) | 100% | 73% | 1/1 | — |
| gptoss | T7_skan.jpg.json | 8 / 8 (wszystkich 11) | 100% | 73% | 1/1 | — |
| gptoss | T7_skan.png.json | 8 / 8 (wszystkich 11) | 100% | 73% | 1/1 | — |
| gptoss | T7_word97.doc.json | 8 / 8 (wszystkich 8) | 100% | 100% | 1/1 | — |
| gptoss | T8.docx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 1/1 | — |
| gptoss | T8.ods.json | 5 / 5 (wszystkich 5) | 100% | 100% | 1/1 | — |
| gptoss | T8.pdf.json | 5 / 5 (wszystkich 10) | 100% | 50% | 1/1 | — |
| gptoss | T8.xlsx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 1/1 | — |
| gptoss | T8_skan.jpg.json | 5 / 5 (wszystkich 8) | 100% | 62% | 1/1 | — |
| gptoss | T8_skan.png.json | 5 / 5 (wszystkich 10) | 100% | 50% | 1/1 | — |
| gptoss | T8_word97.doc.json | 5 / 5 (wszystkich 10) | 100% | 50% | 1/1 | — |
| medium35 | T1.docx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| medium35 | T1.ods.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| medium35 | T1.pdf.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| medium35 | T1.xlsx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| medium35 | T1_skan.jpg.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| medium35 | T1_skan.png.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| medium35 | T1_word97.doc.json | 5 / 5 (wszystkich 5) | 100% | 100% | 2/2 | — |
| medium35 | T2.docx.json | 10 / 10 (wszystkich 10) | 100% | 100% | 1/1 | — |
| medium35 | T2.ods.json | 10 / 10 (wszystkich 10) | 100% | 100% | 1/1 | — |
| medium35 | T2.pdf.json | 10 / 10 (wszystkich 10) | 100% | 100% | 1/1 | — |
| medium35 | T2.xlsx.json | 10 / 10 (wszystkich 10) | 100% | 100% | 1/1 | — |
| medium35 | T2_skan.jpg.json | 7 / 10 (wszystkich 8) | 70% | 88% | 1/1 | Planowany termin usunięcia, Rysunek lub mapa określająca usytuowanie drzewa, Zgoda współwłaściciela nieruchomości (jeżeli dotyczy) |
| medium35 | T2_skan.png.json | 7 / 10 (wszystkich 8) | 70% | 88% | 1/1 | Planowany termin usunięcia, Rysunek lub mapa określająca usytuowanie drzewa, Zgoda współwłaściciela nieruchomości (jeżeli dotyczy) |
| medium35 | T2_word97.doc.json | 10 / 10 (wszystkich 10) | 100% | 100% | 1/1 | — |
| medium35 | T3.docx.json | 4 / 4 (wszystkich 4) | 100% | 100% | 0/0 | — |
| medium35 | T3.ods.json | 4 / 4 (wszystkich 4) | 100% | 100% | 0/0 | — |
| medium35 | T3.pdf.json | 4 / 4 (wszystkich 4) | 100% | 100% | 0/0 | — |
| medium35 | T3.xlsx.json | 4 / 4 (wszystkich 4) | 100% | 100% | 0/0 | — |
| medium35 | T3_skan.jpg.json | 3 / 4 (wszystkich 3) | 75% | 100% | 0/0 | Dowód uiszczenia opłaty skarbowej |
| medium35 | T3_skan.png.json | 3 / 4 (wszystkich 3) | 75% | 100% | 0/0 | Dowód uiszczenia opłaty skarbowej |
| medium35 | T3_word97.doc.json | 4 / 4 (wszystkich 4) | 100% | 100% | 0/0 | — |
| medium35 | T4.docx.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| medium35 | T4.ods.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| medium35 | T4.pdf.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| medium35 | T4.xlsx.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| medium35 | T4_skan.jpg.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| medium35 | T4_skan.png.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| medium35 | T4_word97.doc.json | 6 / 6 (wszystkich 6) | 100% | 100% | 1/1 | — |
| medium35 | T5.docx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| medium35 | T5.ods.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| medium35 | T5.pdf.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| medium35 | T5.xlsx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| medium35 | T5_skan.jpg.json | 4 / 5 (wszystkich 4) | 80% | 100% | 0/0 | Potwierdzenie zapłaty opłaty skarbowej |
| medium35 | T5_skan.png.json | 4 / 5 (wszystkich 4) | 80% | 100% | 0/0 | Potwierdzenie zapłaty opłaty skarbowej |
| medium35 | T5_word97.doc.json | 4 / 5 (wszystkich 4) | 80% | 100% | 0/0 | Potwierdzenie zapłaty opłaty skarbowej |
| medium35 | T6.docx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| medium35 | T6.ods.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| medium35 | T6.pdf.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| medium35 | T6.xlsx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| medium35 | T6_skan.jpg.json | 4 / 5 (wszystkich 4) | 80% | 100% | 0/0 | Kopia dowodu rejestracyjnego |
| medium35 | T6_skan.png.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| medium35 | T6_word97.doc.json | 5 / 5 (wszystkich 5) | 100% | 100% | 0/0 | — |
| medium35 | T7.docx.json | 8 / 8 (wszystkich 8) | 100% | 100% | 1/1 | — |
| medium35 | T7.ods.json | 8 / 8 (wszystkich 8) | 100% | 100% | 1/1 | — |
| medium35 | T7.pdf.json | 8 / 8 (wszystkich 8) | 100% | 100% | 1/1 | — |
| medium35 | T7.xlsx.json | 8 / 8 (wszystkich 8) | 100% | 100% | 1/1 | — |
| medium35 | T7_skan.jpg.json | 8 / 8 (wszystkich 8) | 100% | 100% | 1/1 | — |
| medium35 | T7_skan.png.json | 8 / 8 (wszystkich 8) | 100% | 100% | 1/1 | — |
| medium35 | T7_word97.doc.json | 8 / 8 (wszystkich 8) | 100% | 100% | 1/1 | — |
| medium35 | T8.docx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 1/1 | — |
| medium35 | T8.ods.json | 5 / 5 (wszystkich 5) | 100% | 100% | 1/1 | — |
| medium35 | T8.pdf.json | 5 / 5 (wszystkich 5) | 100% | 100% | 1/1 | — |
| medium35 | T8.xlsx.json | 5 / 5 (wszystkich 5) | 100% | 100% | 1/1 | — |
| medium35 | T8_skan.jpg.json | 5 / 5 (wszystkich 5) | 100% | 100% | 1/1 | — |
| medium35 | T8_skan.png.json | 5 / 5 (wszystkich 5) | 100% | 100% | 1/1 | — |
| medium35 | T8_word97.doc.json | 5 / 5 (wszystkich 5) | 100% | 100% | 1/1 | — |

## Uwagi do interpretacji

- Pola z potwierdzeniem opłaty (T3, T5) generator umieszcza w sekcji opłat na stronie „Opłaty, kontakt i zgody”, którą ocena pomija jako predefiniowaną — ich „brak” to głównie wynik fałszywie ujemny.
- Wnioskodawca: dla T1 (informacja publiczna) i T4 (podatek od nieruchomości) modele dopuszczają także podmiot (firmę), a klucz — tylko osobę; to rozbieżność interpretacji, a nie oczywisty błąd.
- Formularze wygenerowane mają proste, jednoznaczne etykiety, więc modele często je powtarzają — prawdziwe formularze (BIP, materiały wyzwania) są trudniejsze i nie mają klucza odpowiedzi.
