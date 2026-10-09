# Daily News

Minimalistyczny agregator kilku najważniejszych wiadomości z różnych dziedzin.

## Jak działa

1. GitHub Actions uruchamia `scripts/generate_news.py` codziennie.
2. Skrypt pobiera kandydatów z Google News RSS.
3. Gemini wybiera najważniejsze materiały i tworzy krótkie streszczenia na podstawie tytułu i snippetu.
4. Wynik trafia do `data/news.json`.
5. Statyczna strona wyświetla aktualny przegląd.

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

**Settings → Pages → Build and deployment → Deploy from a branch → main / root**

Strona będzie dostępna pod:

```
https://przebindakamil.github.io/daily-news/
```

## Harmonogram

Workflow używa UTC:

```yaml
cron: "15 5 * * *"
```

czyli 05:15 UTC — w Polsce 06:15 zimą lub 07:15 latem.

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
gemini-2.5-flash
```

Model można zmienić przez zmienną `GEMINI_MODEL`.
