# Daily News — roadmap produktu

Cel: **codzienny, pięciominutowy przegląd ważnych informacji**, który pomaga rozumieć wydarzenia bez niekończącego się feedu. Priorytety: **wiarygodność > zrozumienie > wygoda > liczba funkcji**.

**GitHub Issues to źródło prawdy dla otwartych zadań.** Poniższy plan to proponowana kolejność małych wdrożeń, a nie automatyczne zobowiązanie do wypuszczenia funkcji każdego dnia kalendarzowego. Każde zadanie ma zakres, kryteria akceptacji i testy. Po wykonaniu oznacz je jako zakończone w GitHubie oraz zaznacz tutaj.

**Stan na 15.10.2026:** 21 zaplanowanych zadań w 3 etapach; #3 i #4 wykorzystują starsze zgłoszenia zamiast duplikatów. Pierwsze zadanie do podjęcia: **D01, #10**.

## Etap 1 — Wygodne codzienne czytanie (D01–D07)

| Dzień | Zadanie | GitHub Issue | Priorytet | Status |
| --- | --- | --- | --- | --- |
| D01 | Historia wydań w widoku kategorii | [#10](https://github.com/przebindakamil/daily-news/issues/10) | P1 | [ ] |
| D02 | Oznaczanie artykułów jako przeczytane | [#11](https://github.com/przebindakamil/daily-news/issues/11) | P1 | [ ] |
| D03 | Filtr „tylko nieprzeczytane” | [#12](https://github.com/przebindakamil/daily-news/issues/12) | P1 | [ ] |
| D04 | Szacowany czas czytania wiadomości | [#13](https://github.com/przebindakamil/daily-news/issues/13) | P1 | [ ] |
| D05 | Tryb „5 minut” | [#14](https://github.com/przebindakamil/daily-news/issues/14) | P1 | [ ] |
| D06 | Bezpośredni link do artykułu | [#15](https://github.com/przebindakamil/daily-news/issues/15) | P1 | [ ] |
| D07 | Wygodna nawigacja na telefonie | [#16](https://github.com/przebindakamil/daily-news/issues/16) | P1 | [ ] |

**Cel etapu:** mniej tarcia przy czytaniu, zapisanym postępie i udostępnianiu wiadomości. Możliwie bez nowych kosztów API.

## Etap 2 — Jakość i wiarygodność informacji (D08–D14)

| Dzień | Zadanie | GitHub Issue | Priorytet | Status |
| --- | --- | --- | --- | --- |
| D08 | Normalizacja adresów źródłowych | [#17](https://github.com/przebindakamil/daily-news/issues/17) | P1 | [ ] |
| D09 | Łączenie wielu publikacji o jednym wydarzeniu | [#18](https://github.com/przebindakamil/daily-news/issues/18) | P1 | [ ] |
| D10 | Sekcja „Inne źródła” | [#19](https://github.com/przebindakamil/daily-news/issues/19) | P1 | [ ] |
| D11 | Liczba rzeczywiście odrębnych źródeł | [#20](https://github.com/przebindakamil/daily-news/issues/20) | P1 | [ ] |
| D12 | Walidacja dat i linków przed publikacją | [#21](https://github.com/przebindakamil/daily-news/issues/21) | P1 | [ ] |
| D13 | Powtórki między dniami vs. faktyczne aktualizacje | [#22](https://github.com/przebindakamil/daily-news/issues/22) | P1 | [ ] |
| D14 | Kontrola kluczowych liczb i nazwisk | [#23](https://github.com/przebindakamil/daily-news/issues/23) | P1 | [ ] |

**Cel etapu:** mniej duplikatów, wyraźne źródła, mniej błędów. Nie deklarujemy pełnego fact-checku ani „niezależnego potwierdzenia”, jeśli dowody na to nie wystarczają.

## Etap 3 — Ciągłość i rozumienie wydarzeń (D15–D21)

Epic: [#4 Story threads](https://github.com/przebindakamil/daily-news/issues/4) (spina zadania D15–D20).

| Dzień | Zadanie | GitHub Issue | Priorytet | Status |
| --- | --- | --- | --- | --- |
| D15 | Stały identyfikator rozwijającej się historii | [#24](https://github.com/przebindakamil/daily-news/issues/24) | P2 | [ ] |
| D16 | „Wcześniej w tej sprawie” | [#25](https://github.com/przebindakamil/daily-news/issues/25) | P2 | [ ] |
| D17 | Oś czasu wydarzenia | [#26](https://github.com/przebindakamil/daily-news/issues/26) | P2 | [ ] |
| D18 | „Co zmieniło się od ostatniego wydania?” | [#27](https://github.com/przebindakamil/daily-news/issues/27) | P2 | [ ] |
| D19 | Obserwowanie pojedynczego wydarzenia | [#28](https://github.com/przebindakamil/daily-news/issues/28) | P2 | [ ] |
| D20 | Aktualizacje obserwowanych wydarzeń | [#29](https://github.com/przebindakamil/daily-news/issues/29) | P2 | [ ] |
| D21 | Publiczne tygodniowe podsumowanie | [#3](https://github.com/przebindakamil/daily-news/issues/3) | P2 | [ ] |

**Cel etapu:** czytelnik wie, co się zmieniło i co wydarzyło się wcześniej, bez ponownego odtwarzania kontekstu. Tygodniowy skrót publiczny to inny produkt niż **prywatny audyt administratora**.

## Następne priorytety i mierzenie postępu

- [ ] [#30 Prywatnościowa analityka i KPI](https://github.com/przebindakamil/daily-news/issues/30): powracający czytelnicy, realne używanie nowych funkcji i jakość korzystania z produktu.
- [ ] [#6 Profil zainteresowań uczący się z jawnego feedbacku](https://github.com/przebindakamil/daily-news/issues/6): uzupełniać nową logikę plus/minus, nie zmieniać po cichu ręcznych wag czytelnika.
- [ ] [#5 Personalizacja embeddings](https://github.com/przebindakamil/daily-news/issues/5): sprawdzić zysk jakościowy i koszty, zanim dołożymy nową warstwę.
- [ ] [#7 Opcjonalne codzienne powiadomienie TOP 3](https://github.com/przebindakamil/daily-news/issues/7): bez wymuszania zgód.
- [ ] [#9 Wyszukiwanie źródeł na podstawie własnych zainteresowań](https://github.com/przebindakamil/daily-news/issues/9): dopiero gdy mamy sensowny backend i zabezpieczenia.

**Miary sukcesu:** częstotliwość powrotów, ukończenie krótkiego briefingu, używanie linków do źródeł, liczba duplikatów między wydaniami, pokrycie ważnych wydarzeń na bazie ostrożnego audytu, niezawodność publikacji i stabilność UI. Metryki zachowania użytkowników wymagają osobnego, prywatnościowego pomiaru (#30); nie udajemy, że obecnie je znamy.

## Dalszy backlog — po weryfikacji użyteczności

- [ ] [#31 PWA i instalacja na telefonie](https://github.com/przebindakamil/daily-news/issues/31)
- [ ] [#32 Ostatnie wydanie offline](https://github.com/przebindakamil/daily-news/issues/32)
- [ ] [#33 Odsłuchiwanie krótkiego przeglądu](https://github.com/przebindakamil/daily-news/issues/33)
- [ ] [#34 Newsletter na życzenie](https://github.com/przebindakamil/daily-news/issues/34)
- [ ] [#35 Konto i synchronizacja między urządzeniami](https://github.com/przebindakamil/daily-news/issues/35)
- [ ] Własna domena/SEO — dopiero gdy będziemy skalować odbiorców i uporządkujemy obecne wdrożenia.
- [ ] Rozszerzone objaśnienie „dlaczego to ważne dla mnie” — dopiero po wdrożeniu ciągłości historii i ocenie kosztu Gemini.

## Ukończone i działające

- [x] Codzienny workflow Gemini + bezpośrednia publikacja GitHub Pages
- [x] Globalny ranking i automatyczna selekcja z RSS/Google News oraz źródeł pierwotnych
- [x] Archiwum dzień po dniu i wyszukiwanie w archiwum
- [x] Kategorie, TOP dnia, tagi tematyczne i szerszy katalog kategorii
- [x] Personalizacja po stronie przeglądarki, onboarding, gotowe presety i „Poza twoją bańką”
- [x] Dostosowywanie liczby materiałów, włączanie i wyłączanie kategorii oraz własne zainteresowania
- [x] Rozwijana „Wiedza w pigułce” i lista zapisanych artykułów
- [x] „+ / −”: można cofnąć ocenę, głosy wpływają na przyszłe układy, nie przestawiają bieżącej listy
- [x] Zapis artykułu bez zamykania rozwiniętej treści; stabilniejsze karty przy interakcjach
- [x] Tygodniowy audyt redakcyjny administratora z szyfrowanymi raportami
- [x] Kontrola błędów Gemini 429 i unikanie zbędnych dodatkowych żądań
- [x] Testy Pythona i JavaScript w GitHub Actions

## Reguła „jedna funkcja dziennie”

1. Bierz pierwsze otwarte Issue z harmonogramu, uwzględniając zależności.
2. Wykonaj tylko zakres tego issue — bez równoczesnego przebudowywania architektury.
3. Dodaj adekwatne testy regresyjne (Python / JavaScript), a dla widoków sprawdź również stabilność i mobile.
4. Wymagaj poprawnego CI i działającego wdrożenia; prywatny audyt nie może stać się publiczny.
5. Dopiero po weryfikacji zamknij Issue i oznacz [x] w tej roadmapie.

Pierwszy krok: [D01 — Historia wydań w widoku kategorii, #10](https://github.com/przebindakamil/daily-news/issues/10).
