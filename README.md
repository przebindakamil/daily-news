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
