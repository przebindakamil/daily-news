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

Po każdym wygenerowaniu wydania skrypt zapisuje raport:
`reports/coverage/YYYY-MM-DD.json`.

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

Krótkie podsumowanie trafia także na stronę uruchomienia GitHub Actions,
w sekcji **Job summary**. Lista wykrytych możliwych luk jest sygnałem do
sprawdzenia, a nie automatycznym dowodem błędu. Brak ostrzeżeń **nie
gwarantuje** pokrycia wszystkich wydarzeń na świecie.

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

## Tygodniowy audyt i dashboard

Strona ma osobną zakładkę **Audyt** (adres `#audit`) z historią raportów
oraz bezpośrednimi adresami tygodni, np. `#audit/2026-W41`.

Widok obejmuje:
- porównanie pokrycia istotnych wydarzeń w kolejnych tygodniach;
- statusy: **uwzględnione**, **częściowo opisane**, **pominięte**;
- wyniki według kategorii, dzienne statystyki publikacji i duplikaty;
- źródła wydarzeń oraz informację, na którym etapie selekcji je znaleziono;
- oznaczenie tygodni z niepełnymi danymi (bez fikcyjnego procentu pokrycia).

### Harmonogram audytu

Workflow `.github/workflows/weekly-audit.yml` działa w poniedziałek
o **08:00 czasu Europe/Warsaw**. Audytuje zakończony tydzień
(poniedziałek–niedziela), po zakończeniu publikacji niedzielnego wydania
przez poranny workflow Daily News.

Skrypt `scripts/audit_news.py` pobiera:
1. 7 wydań z `data/archive/`;
2. 7 dziennych raportów `reports/coverage/`, w tym niezależne nagłówki
   z Polski i świata oraz listy pobranych kandydatów;
3. wybiera przez Gemini do 25 kluczowych, różnych wydarzeń źródłowych;
4. semantycznie dopasowuje je do publikacji i oznacza potencjalne pominięcia.

Zapisuje `reports/audits/YYYY-Www.json` oraz `reports/audits/index.json`.
Po commicie uruchamia bezpośrednie wdrożenie GitHub Pages, dzięki czemu
nowy tydzień pojawia się na dashboardzie bez ręcznych działań.

Ręczne wygenerowanie audytu: **Actions → Weekly editorial audit → Run workflow**.
Opcjonalne pole `week` przyjmuje `YYYY-Www` dla zakończonego tygodnia.

### Jak interpretować wyniki?

Wskaźnik pokrycia jest **szacunkiem na próbce nagłówków**, a nie
stwierdzeniem, że system wychwycił określony procent wszystkich ważnych
wiadomości na świecie. Częściowe uwzględnienie daje 0,5 punktu.
Nie mierzymy tutaj automatycznie poprawności faktograficznej artykułów.

Pełny wynik obliczamy wyłącznie wtedy, gdy mamy 7 wydań, 7 raportów
źródeł oraz niezależne nagłówki ze wszystkich siedmiu dni.
Inne tygodnie pokazują dostępne dane operacyjne i status **niepełny**.
Historyczne wydanie za tydzień `2026-W41` zawiera tylko informacje,
które rzeczywiście zostały zachowane (9–11 października).

Poprawki do rankingów lub automatyczna publikacja wykrytych pominięć
**nie odbywają się bez dodatkowej weryfikacji**.
