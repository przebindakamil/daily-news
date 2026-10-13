# Daily News

Minimalistyczny, personalizowany briefing najważniejszych i najciekawszych informacji z wielu źródeł.

## Jak działa

1. GitHub Actions uruchamia `scripts/generate_news.py` codziennie o 06:00 czasu polskiego, zbierając wiadomości za cały poprzedni dzień.
2. Skrypt buduje pulę z wielu źródeł: bezpośrednich RSS renomowanych mediów i źródeł pierwotnych, zaufanych domen wyszukiwanych przez Google News oraz szerokiego Google News jako fallbacku.
3. Gemini ocenia znaczenie, nowość, użyteczność, jakość źródła i to, czy materiał jest naprawdę wart czasu czytelnika, a następnie tworzy skróty i „wiedzę w pigułce”.
4. Wynik trafia do `data/news.json` oraz archiwum pod datą dnia, którego dotyczą wiadomości.
5. W ramach tego samego workflow GitHub Actions wdraża nową wersję strony na GitHub Pages.

## Wymagany sekret

W repozytorium przejdź do:

**Settings → Secrets and variables → Actions → New repository secret**

Dodaj sekret:

```
GEMINI_API_KEY
```

Wartość: Twój klucz Gemini API.

Nie zapisuj klucza w kodzie ani w `.env` w repozytorium.

## Test ręczny

Po dodaniu sekretu:

**Actions → Daily news → Run workflow**

Po poprawnym wykonaniu powinien pojawić się commit:

```
Update daily news
```

## GitHub Pages

W repozytorium:

**Settings → Pages → Build and deployment → Source → GitHub Actions**

Strona będzie dostępna pod:

```
https://przebindakamil.github.io/daily-news/
```

## Harmonogram i publikacja

Workflow uruchamia się **codziennie o 06:00 czasu polskiego**, automatycznie
uwzględniając czas letni i zimowy:

```yaml
schedule:
  - cron: "0 6 * * *"
    timezone: "Europe/Warsaw"
```

Każde uruchomienie opracowuje **pełny poprzedni dzień kalendarzowy w Polsce**
(od 00:00 włącznie do 00:00 następnego dnia wyłącznie). Przykładowo:
14 października o 06:00 skrypt generuje wydanie oznaczone datą 13 października.

Wiadomości bez możliwej do ustalenia daty publikacji nie są dodawane do zestawu.
Skrypt pobiera RSS oraz wyniki Google News z wystarczająco szerokiego okresu,
po czym filtruje je dokładnie według daty i strefy czasowej.

Po zakończeniu selekcji i redakcji w **tym samym workflow** następuje:
1. Zapis `data/news.json`, `data/current.json` i `data/archive/<data>.json`;
2. Commit wygenerowanych wiadomości do gałęzi `main`;
3. Spakowanie strony statycznej z aktualnymi danymi;
4. Bezpośrednie wdrożenie GitHub Pages przez `actions/deploy-pages`.

**Ważne:** w ustawieniach repozytorium w `Settings → Pages → Build and deployment → Source`
należy wybrać **GitHub Actions** (zamiast `Deploy from a branch`).
Committowanie plików przez `GITHUB_TOKEN` samo w sobie nie wyzwala
wdrożenia GitHub Pages z gałęzi.

GitHub Actions może rozpocząć wykonanie z opóźnieniem względem 06:00.
Publikacja pojawi się po wykonaniu wszystkich kroków i pomyślnym deployu,
niekoniecznie dokładnie o 06:00.

Test ręczny: `Actions → Daily news → Run workflow`. Powtórne uruchomienie
tego samego dnia może ponownie wygenerować wydanie za wczoraj.

## Kontrola pominiętych ważnych wiadomości

Po każdym wygenerowaniu wydania skrypt przygotowuje wewnętrzny raport
`reports/coverage/YYYY-MM-DD.json`, a przed commitem szyfruje go do
`secure/coverage/YYYY-MM-DD.enc.json` (wymaga sekretu `AUDIT_PASSWORD`).

Raport pokazuje:
- ile wiadomości zebrały poszczególne źródła RSS i zapytania Google News;
- czy któreś źródło zwróciło pusty kanał / ostrzeżenie parsera;
- ile kandydatów znaleziono, ile oceniono i ile ostatecznie opublikowano;
- jakie tematy wykryto, lecz odpadły w selekcji (m.in. Nagrody Nobla,
  wyniki wyborów, decyzje banków centralnych, katastrofy i rozejmy);
- 15 najwyżej ocenianych wiadomości, które nie weszły do finalnego wydania.
- niezależne zestawienie głównych nagłówków Google News z Polski i świata,
  z oznaczeniem tych, których nie można dopasować do wydania po URL lub tytule.
  Niedopasowane nagłówki wymagają oceny człowieka, bo mogą być tą samą
  historią opublikowaną pod innym tytułem.

Szczegóły raportu pozostają prywatne; nie zapisujemy ich w publicznych
podsumowaniach GitHub Actions. Lista możliwych luk jest sygnałem do
sprawdzenia, a nie dowodem błędu. Brak ostrzeżeń **nie gwarantuje**
pokrycia wszystkich wydarzeń na świecie.

Zbieranie źródeł rozszerzono o niezależne kanały tematyczne Guardian,
monitorowane zapytania dotyczące Nagrody Nobla i PAP oraz dwa kanały
nagłówków dnia Google News (Polska / świat). Wydanie nadal ogranicza się
do pełnego poprzedniego dnia według strefy Europe/Warsaw.

## Kategorie

Domyślnie publikowane są 2 materiały z każdej kategorii:

- AI i technologia
- Polska i świat
- Piłka nożna i sport
- Finanse i biznes
- Nauka
- Kultura

Liczbę można zmienić przez `NEWS_PER_CATEGORY`.

## Konfiguracja modelu

Domyślnie używany jest:

```
gemini-3.5-flash-lite
```

Model można zmienić przez zmienną `GEMINI_MODEL`.

## Prywatny audyt administratora

**Audyt nie jest elementem publicznej nawigacji.** Publiczny serwis nadal
działa bez logowania. Wewnętrzny dashboard ma nieudostępniany w nawigacji
adres `#audit`, na którym przed odczytem jakichkolwiek raportów wymagane
jest hasło administratora.

GitHub Pages i repozytorium Daily News są publiczne. Nie wystarczy ukryć
zakładki lub ochronić jej wyłącznie JavaScriptem — pliki JSON muszą być
zaszyfrowane. Dlatego prywatne raporty są szyfrowane na runnerze GitHub
Actions przez AES-256-GCM, z kluczem wyprowadzonym z hasła za pomocą
PBKDF2-SHA256 (250 000 iteracji, losowa sól i nonce dla każdego pliku).
Publiczne repozytorium przechowuje tylko zaszyfrowane raporty.
Hasło nie trafia do kodu, commitów ani hostingu.

**Wymagane jednorazowe ustawienie:**
1. Otwórz `Settings → Secrets and variables → Actions → New repository secret`.
2. Nazwa: `AUDIT_PASSWORD`.
3. Wartość: silne, unikatowe hasło **minimum 16 znaków**,
   zalecane co najmniej 24 losowe znaki lub długie hasło z menedżera haseł.
   Nie dodawaj hasła do kodu i nie wklejaj go do czatu.
4. Zapisz sekret i uruchom ręcznie `Actions → Daily news → Run workflow`,
   by utworzyć pierwszy zaszyfrowany raport dzienny.
5. Jeśli chcesz już teraz uruchomić historyczny audyt, wybierz
   `Actions → Weekly editorial audit → Run workflow`
   i w polu `week` wpisz np. `2026-W41`.
   Powstanie raport niepełny (część danych historycznych nie istnieje).
6. Otwórz `https://przebindakamil.github.io/daily-news/#audit`
   i użyj hasła `AUDIT_PASSWORD` w formularzu administratora.

Nie przechowujemy hasła w `localStorage`; po odświeżeniu strony
należy podać je ponownie. Znajomość hasła oznacza dostęp do audytu,
więc **to ochrona współdzielonym hasłem, nie pełny system indywidualnych
kont administratorów**. Jeśli w przyszłości będzie więcej osób
z różnymi uprawnieniami, użyj prywatnego backendu i autoryzacji kont.

### Harmonogram i historia

Codzienne wydanie (06:00) szyfruje raport diagnostyczny w
`secure/coverage/YYYY-MM-DD.enc.json`. Przy braku skonfigurowanego
hasła prywatny raport jest odrzucany, ale publiczne newsy wciąż się
publikują. Tygodniowy audyt (poniedziałek 08:00) odszyfrowuje siedem
raportów dziennych w pamięci roboczej runnera, porównuje je z wydaniami
i szyfruje wyniki do `secure/audits/YYYY-Www.enc.json` oraz
`secure/audits/index.enc.json`. Pliki jawne są usuwane przed commitem.
Dashboard po wpisaniu hasła odczytuje raporty w przeglądarce.

Raporty obejmują historię, trend jakości, pominięte wydarzenia,
pokrycie według kategorii, diagnostykę źródeł i duplikaty.
Wskaźnik pokrycia mierzy **próbkę niezależnych nagłówków**, nie wszystkie
ważne wydarzenia na świecie. Tydzień niekompletny ma status `incomplete`
i nie otrzymuje fikcyjnej wartości procentowej.

### Ważne ograniczenie historyczne

Wcześniej jawne raporty istniały w publicznym repozytorium
`reports/audits/`. Zostały usunięte z aktualnej gałęzi i z nowych
wdrożeń, ale ich kopie mogą nadal być dostępne **w historii commitów**,
archiwach i cache. Aby usunąć je także z historii repozytorium,
konieczna jest osobna migracja / przepisanie historii oraz
uwzględnienie możliwych kopii. Nie można zagwarantować cofnięcia
wcześniejszego publicznego udostępnienia.
