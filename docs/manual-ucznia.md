# AI Exam Tutor - manual ucznia

**Wersja manuala:** 1.0  
**Dotyczy aplikacji:** AI Exam Tutor 1.0.0  
**Platforma:** Windows

Ten manual opisuje korzystanie z gotowej wersji aplikacji dla ucznia przygotowującego się do egzaminu INF.03. Aplikacja pozwala otworzyć arkusz PDF, pracować nad SQL oraz kodem PHP/HTML, zadawać pytania tutorowi AI i sprawdzić rozwiązanie.

Językiem domyślnym aplikacji jest polski. Nazwy menu, przycisków i pól w tym dokumencie odpowiadają polskiej wersji interfejsu. Wersja `English` używa odpowiedników angielskich.

> **Ważne:** ten dokument jest żywą dokumentacją projektu. Przy każdej zmianie wpływającej na instalację, konfigurację AI, interfejs, skróty klawiaturowe, obsługę PDF, workflow INF.03, ocenianie albo zapisywanie danych należy zaktualizować również ten manual.

## 1. Zanim zaczniesz

Przygotuj:

- komputer z systemem Windows;
- instalator `AI_Exam_Tutor_Setup.exe`;
- arkusz egzaminacyjny INF.03 w formacie PDF;
- osobny klucz odpowiedzi w formacie PDF, jeśli chcesz użyć funkcji `Sprawdź zadanie`;
- dostęp do jednego z dostawców AI:
  - własny klucz API do usługi chmurowej, albo
  - działający lokalnie program z modelem AI, na przykład Ollama lub LM Studio;
- XAMPP z uruchomionym modułem MySQL, jeśli chcesz wykonywać zapytania SQL na lokalnej bazie.

Aplikacja nie uruchamia automatycznie XAMPP ani MySQL. Nie pobiera też automatycznie najnowszych arkuszy CKE.

### Arkusze CKE

Wybieraj materiały z legalnego źródła, najlepiej z oficjalnej strony Centralnej Komisji Egzaminacyjnej albo od nauczyciela. Wersja projektu opisywana tym manualem nie zawiera jeszcze przykładowego arkusza PDF do otwarcia. Zasady dotyczące materiałów archiwalnych opisano w pliku [LICENSE_NOTICE.md](../resources/exam_sheets/LICENSE_NOTICE.md).

## 2. Instalacja aplikacji

1. Odszukaj plik `AI_Exam_Tutor_Setup.exe`.
2. Uruchom instalator dwuklikiem.
3. Wybierz język instalatora.
4. Przejdź przez kolejne ekrany instalacji.
5. Jeżeli chcesz, zaznacz utworzenie skrótu na pulpicie.
6. Po zakończeniu instalacji uruchom aplikację z menu Start albo ze skrótu.

Instalator nie powinien wymagać uprawnień administratora. Domyślna nazwa programu to **AI Exam Tutor**.

## 3. Pierwsze uruchomienie

Po uruchomieniu zobaczysz główne okno podzielone na trzy części:

| Część okna | Zastosowanie |
|---|---|
| Lewa | Podgląd arkusza PDF |
| Środkowa | Środowisko egzaminacyjne, czyli SQL oraz edytory PHP/HTML |
| Prawa | Rozmowa z `AI Tutor (sokratejski)` |

Przy pierwszym uruchomieniu wykonaj te czynności w kolejności:

1. Otwórz `Plik -> Ustawienia` albo użyj skrótu `Ctrl+,`.
2. Sprawdź, czy w polu `Język` wybrano `Polski`. Jest to ustawienie domyślne.
3. Skonfiguruj dostawcę AI według rozdziału 4.
4. Otwórz arkusz przez `Plik -> Otwórz PDF` albo skrót `Ctrl+O`.
5. Jeżeli chcesz oceniać zadanie, otwórz również `Plik -> Otwórz PDF z kluczem odpowiedzi`.
6. W środkowym panelu pozostaw lub wybierz środowisko `INF.03 - SQL i PHP/HTML`.
7. Wyślij krótkie pytanie testowe do tutora, na przykład: `Jakie wymagania powinienem sprawdzić w tym zadaniu?`.

Aplikacja zapamiętuje wybrane ustawienia oraz ostatnio używane pliki. Przy kolejnym uruchomieniu spróbuje przywrócić poprzedni arkusz PDF i środowisko pracy.

## 4. Konfiguracja AI

### 4.1 Otwieranie ustawień

Wybierz `Plik -> Ustawienia` lub naciśnij `Ctrl+,`. Okno ustawień zawiera pola:

| Pole | Co wpisać |
|---|---|
| `Dostawca` | Dostawcę usługi AI albo lokalnego serwera |
| `Model` | Dokładną nazwę modelu dostępnego u wybranego dostawcy |
| `Klucz API` | Klucz API usługi chmurowej; dla lokalnego serwera zwykle pozostaw puste |
| `Adres bazowy` | Adres API dostawcy; zwykle jest uzupełniany automatycznie |
| `Język` | Język interfejsu: `Polski` albo `English` |

Po wybraniu dostawcy lista modeli zostanie odświeżona. Pole `Model` jest edytowalne, więc można wpisać model, którego nie ma na liście, jeżeli dostawca go obsługuje. Kliknij `Testuj połączenie`, aby sprawdzić bieżące, jeszcze niezapisane dane połączenia. Kliknij `Zapisz`, aby zachować ustawienia.

Zmiana pola `Język` zostaje zapisana razem z pozostałymi ustawieniami, ale wymaga ponownego uruchomienia aplikacji. Po zapisaniu wyboru zamknij i uruchom AI Exam Tutor ponownie. Polski jest używany automatycznie, jeżeli nie zapisano jeszcze żadnego języka.

### 4.2 Dostawcy i adresy

| Dostawca | Domyślny `Adres bazowy` | Przykładowe modele | Klucz API |
|---|---|---|---|
| `OpenAI` | `https://api.openai.com/v1` | `gpt-4o`, `gpt-4o-mini` | Wymagany |
| `Google Gemini` | `https://generativelanguage.googleapis.com/v1beta` | `gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-1.5-flash-8b` | Wymagany |
| `OpenRouter` | `https://openrouter.ai/api/v1` | `openai/gpt-4o-mini`, `openai/gpt-4o` | Wymagany |
| `Groq` | `https://api.groq.com/openai/v1` | `llama-3.2-11b-vision`, `llama-3.1-70b-versatile` | Wymagany |
| `LM Studio` | `http://localhost:1234/v1` | `local-model` albo nazwa załadowanego modelu | Zwykle nie |
| `Ollama` | `http://localhost:11434/v1` | `llava`, `llama3.2` | Nie |
| `OmniRoute` | `http://localhost:20128/v1` | `local-model` albo nazwa dostępnego modelu | Zależnie od konfiguracji |
| `Własny zgodny z OpenAI` | Puste | Nazwa modelu z własnego serwera | Zależnie od konfiguracji |

Dla `Własny zgodny z OpenAI` trzeba samodzielnie uzupełnić `Adres bazowy`. Adres powinien wskazywać API zgodne z formatem OpenAI, a nie zwykłą stronę internetową.

### 4.3 Wariant chmurowy

1. Utwórz konto u wybranego dostawcy.
2. Wygeneruj klucz API w panelu tego dostawcy.
3. W aplikacji wybierz odpowiedniego `Dostawcę`.
4. Wybierz lub wpisz dostępny `Model`.
5. Wklej klucz do pola `Klucz API`.
6. Sprawdź `Adres bazowy`.
7. Kliknij `Zapisz`.
8. Wyślij pytanie testowe do tutora.

Usługi chmurowe mogą pobierać opłaty za wysłane zapytania i obrazy. Sprawdź limity oraz cennik przed rozpoczęciem pracy. AI Exam Tutor nie dostarcza klucza API ani nie opłaca konta u zewnętrznego dostawcy.

### 4.4 Wariant lokalny

Wariant lokalny nie wymaga klucza API, ale wymaga uruchomionego programu AI na tym samym komputerze:

1. Uruchom Ollama, LM Studio albo inny obsługiwany serwer.
2. Pobierz lub załaduj model w tym programie.
3. Sprawdź, czy serwer nasłuchuje na właściwym porcie.
4. W AI Exam Tutor wybierz odpowiedniego `Dostawcę`.
5. Wpisz dokładną nazwę załadowanego modelu w polu `Model`.
6. Pozostaw `Klucz API` puste, chyba że lokalny serwer wymaga klucza.
7. Sprawdź `Adres bazowy` i kliknij `Zapisz`.
8. Wyślij pytanie testowe.

Lokalny provider może działać bez internetu, ale wymaga wystarczającej ilości pamięci i mocy obliczeniowej komputera. Aplikacja nie pobiera modeli za użytkownika.

### 4.5 Model obsługujący obrazy

Praca z arkuszami, wycinkami stron PDF oraz zadaniami wymagającymi analizy obrazu wymaga modelu z obsługą vision. Przykładowe modele rozpoznawane przez aplikację to:

- `gpt-4o` i `gpt-4o-mini`;
- `gemini-1.5-flash`, `gemini-1.5-pro` i `gemini-1.5-flash-8b`;
- `llama-3.2-11b-vision`;
- `llava` i `llava:13b`;
- `qwen2-vl`.

Jeżeli wybrany model nie znajduje się na liście modeli vision aplikacji, na pasku stanu może pojawić się ostrzeżenie. Zwykły model tekstowy może odpowiadać na pytania tekstowe, ale nie musi poprawnie analizować obrazu.

### 4.6 Bezpieczeństwo klucza API

Klucz API jest zapisywany lokalnie w bazie konfiguracji aplikacji razem z pozostałymi ustawieniami. Nie wysyłaj go tutorowi w wiadomości, nie publikuj go na zrzucie ekranu i nie udostępniaj innym osobom.

Aplikacja nie jest menedżerem haseł i manual nie zakłada szyfrowania klucza w lokalnej bazie. Jeżeli klucz wycieknie, natychmiast unieważnij go w panelu dostawcy i utwórz nowy.

## 5. Praca z PDF-em

### Otwieranie arkusza

1. Wybierz `Plik -> Otwórz PDF` albo naciśnij `Ctrl+O`.
2. Wskaż plik PDF arkusza.
3. Po załadowaniu użyj pola `Strona`, aby przejść do wybranej strony.
4. Użyj pola `Powiększenie`, aby zmienić powiększenie.

Dostępne poziomy powiększenia to `75%`, `100%`, `150%`, `200%` i `300%`. Możesz również używać `Ctrl++`, `Ctrl+-` oraz `Ctrl+0`.

### Otwieranie klucza odpowiedzi

Wybierz `Plik -> Otwórz PDF z kluczem odpowiedzi` i wskaż osobny PDF z kluczem odpowiedzi. Klucz jest używany jako kontekst tutora i jako materiał odniesienia podczas `Sprawdź zadanie`.

Sam arkusz egzaminacyjny i klucz odpowiedzi to dwa różne pliki. Załadowanie tylko arkusza nie wystarczy do automatycznego oceniania.

### Wycinek strony dla tutora

Aby wysłać tutorowi fragment arkusza:

1. Otwórz właściwą stronę PDF.
2. Kliknij `Zaznacz fragment (Ctrl+Shift+S)` albo naciśnij `Ctrl+Shift+S`.
3. Przeciągnij myszą po interesującym fragmencie.
4. Puść przycisk myszy.
5. Napisz pytanie w panelu AI Tutor i kliknij `Wyślij`.

Wycinek zostanie dołączony do następnej wiadomości. Aby anulować zaznaczanie, naciśnij `Esc`.

Jeżeli aplikacja pokazuje `PyMuPDF not available`, bieżący pakiet nie ma składnika potrzebnego do wyświetlania PDF-ów. Skontaktuj się z osobą przygotowującą instalator, zamiast instalować przypadkowe dodatki z internetu.

## 6. Sesja INF.03

### 6.1 Rozpoczęcie pracy

Po uruchomieniu środowiska INF.03 aplikacja tworzy bieżącą próbę egzaminacyjną. W środkowym panelu znajdziesz:

- wybór schematu bazy danych;
- pole `Połączenie`;
- przyciski `Zapisz` i `Testuj`;
- edytor SQL oraz tabelę wyników;
- zakładki `index.php` i `index.html`;
- zakładkę `style.css` dla arkusza stylów;
- przyciski `Zapisz bieżący plik`, `Sprawdź zadanie` i `Uruchom w przeglądarce`.

### 6.2 XAMPP i MySQL

AI Exam Tutor jest klientem MySQL. Przed użyciem zapytań:

1. Uruchom XAMPP Control Panel.
2. Kliknij `Uruchom` przy module `MySQL`.
3. Upewnij się, że baza i tabela potrzebne do zadania istnieją.
4. W aplikacji uzupełnij pole `Połączenie`.

Domyślny format połączenia to:

```text
mysql://user:password@host:3306/database
```

Dla typowej lokalnej instalacji XAMPP może to być na przykład:

```text
mysql://root:@localhost:3306/nazwa_bazy
```

Znaczenie elementów:

- `user` - użytkownik MySQL;
- `password` - hasło użytkownika, po dwukropku;
- `host` - zwykle `localhost`;
- `3306` - standardowy port MySQL;
- `database` - nazwa bazy danych.

Kliknij `Testuj`, aby sprawdzić połączenie. Jeżeli test się nie powiedzie, sprawdź, czy MySQL działa, czy port jest prawidłowy oraz czy dane logowania są poprawne. Kliknij `Zapisz`, aby zapamiętać połączenie.

### 6.3 Wykonywanie SQL

1. Wybierz schemat w polu `Schemat`, jeżeli jest dostępny.
2. Wpisz zapytanie w edytorze SQL.
3. Kliknij `Uruchom SQL (Ctrl+Enter)` albo naciśnij `Ctrl+Enter`.
4. Obejrzyj wynik w tabeli poniżej edytora.

Po poprawnym wykonaniu aplikacja pokazuje liczbę zwróconych wierszy i czas wykonania. Możesz umieścić w edytorze kilka instrukcji rozdzielonych średnikiem `;`.

Błąd MySQL nie oznacza błędu tutora AI. Najpierw sprawdź połączenie z lokalną bazą oraz składnię zapytania.

### 6.4 Edytory PHP i HTML

Pracuj w odpowiedniej zakładce:

- `index.php` dla kodu PHP;
- `index.html` dla kodu HTML.
- `style.css` dla stylów CSS.

Szkice są automatycznie zapisywane po krótkiej przerwie w pisaniu. Dzięki temu treść może zostać odtworzona po ponownym wejściu do tej samej próby.

`Zapisz bieżący plik` zapisuje aktualnie wybraną zakładkę jako plik na dysku. Jest to osobna czynność od automatycznego zapisu szkicu w bazie aplikacji. Wybierz tę opcję, gdy chcesz zachować plik w konkretnym folderze albo użyć go poza aplikacją.

`Uruchom w przeglądarce` zapisuje aktualną treść do katalogu tymczasowego i otwiera plik w domyślnej przeglądarce. Jest to szybki podgląd pliku. Nie zastępuje pełnego serwera PHP i nie uruchamia automatycznie interpretera PHP.

## 7. Rozmowa z AI Tutor

Panel po prawej stronie działa w trybie `AI Tutor (sokratejski)`. Tutor ma pomagać w rozumowaniu, a nie od razu podawać kompletne rozwiązanie.

Aby zadać pytanie:

1. Wpisz pytanie w polu `Ask the AI Tutor...`.
2. Kliknij `Send (Ctrl+Enter)` albo naciśnij `Ctrl+Enter`.
3. Poczekaj na odpowiedź.

Do wiadomości tutora może zostać automatycznie dołączony bieżący kontekst środowiska pracy, w tym:

- treść zapytania SQL;
- kod PHP;
- kod HTML;
- wybrany schemat;
- tekst arkusza i klucza odpowiedzi, jeżeli jest dostępny.

Historia rozmowy jest przechowywana dla bieżącej próby. Nie wpisuj do rozmowy haseł, kluczy API ani innych poufnych danych.

Jeżeli tutor nie odpowiada, sprawdź konfigurację w `Ustawienia`, dostęp do internetu albo działanie lokalnego dostawcy. Podczas oczekiwania przycisk wysyłania może mieć nazwę `Myślę...`.

## 8. Sprawdzanie rozwiązania

Przed użyciem `Sprawdź zadanie`:

1. Otwórz arkusz egzaminacyjny.
2. Otwórz `PDF z kluczem odpowiedzi`.
3. Uzupełnij SQL, PHP i HTML.
4. Zapisz bieżące pliki, jeżeli chcesz mieć kopię na dysku.
5. Upewnij się, że provider AI i model działają.
6. Kliknij `Sprawdź zadanie`.

Podczas oceniania przycisk zmieni nazwę na `Sprawdzanie...`, a aplikacja pokaże komunikat o sprawdzaniu rozwiązania. Ocena jest wykonywana w tle, więc okno aplikacji nie powinno się zawiesić.

Po poprawnym wyniku zobaczysz:

- wynik całkowity, na przykład `Score: 8/10 (80%)`;
- podział na kryteria;
- informację zwrotną;
- listę brakujących wymagań;
- podsumowanie.

Poprawny wynik zostaje zapisany w bieżącej próbie. Jeżeli evaluator zwróci niepoprawny JSON albo wystąpi błąd sieci, wynik może nie zostać zapisany. W takiej sytuacji popraw konfigurację AI i spróbuj ponownie.

`Sprawdź zadanie` jest pomocą w nauce. Nie traktuj wyniku modelu AI jako oficjalnej oceny egzaminacyjnej.

## 9. Motyw i zapisywanie danych

Motyw zmienisz przez `Plik -> Zmień motyw` albo skrót `Ctrl+T`.

Aplikacja przechowuje lokalnie:

- ustawienia dostawcy, modelu, adresu API i klucza;
- wybrany arkusz oraz klucz odpowiedzi;
- aktywne środowisko pracy;
- historię wiadomości w bieżących próbach;
- szkice SQL, PHP i HTML;
- wyniki zakończonego oceniania.

Dane są przechowywane w lokalnej bazie SQLite `exam_tutor.db` używanej przez aplikację. Nie usuwaj tego pliku, jeżeli chcesz zachować ustawienia, historię i szkice. Nie przenoś go bez potrzeby między różnymi instalacjami, ponieważ zapisane ścieżki do PDF-ów mogą przestać działać.

## 10. Najczęstsze problemy

| Objaw | Co sprawdzić |
|---|---|
| Tutor nie odpowiada | `Dostawca`, `Model`, `Adres bazowy`, klucz API, internet albo działanie lokalnego serwera |
| Błąd autoryzacji | Czy klucz jest aktualny, poprawnie wklejony i czy konto ma dostęp do modelu |
| Błąd połączenia sieciowego | Czy adres `Adres bazowy` jest prawidłowy i czy dostawca działa |
| Ostrzeżenie o vision | Wybierz model obsługujący obrazy, na przykład `gpt-4o`, `gemini-1.5-flash` albo `llava` |
| PDF się nie otwiera | Sprawdź plik i komunikat `PyMuPDF not available`; w drugim przypadku potrzebny jest poprawnie zbudowany instalator |
| MySQL nie odpowiada | Uruchom MySQL w XAMPP, sprawdź port, użytkownika, hasło, nazwę bazy i kliknij `Testuj` |
| Nie działa `Sprawdź zadanie` | Najpierw otwórz `PDF z kluczem odpowiedzi`, potem sprawdź dostawcę i model |
| Wynik oceniania jest pusty lub niepoprawny | Ponów próbę; model musi zwrócić poprawny format odpowiedzi, a połączenie musi działać |
| Nie ma zapisanych szkiców | Otwórz tę samą próbę i sprawdź, czy aplikacja nie korzysta z innego pliku `exam_tutor.db` |
| `Uruchom w przeglądarce` nie wykonuje PHP | Funkcja otwiera plik w przeglądarce, ale nie uruchamia serwera PHP; użyj lokalnego serwera, jeżeli zadanie tego wymaga |

## 11. Krótka checklista przed nauką

- [ ] Aplikacja uruchamia się bez błędu.
- [ ] Dostawca, model i `Adres bazowy` są ustawione.
- [ ] Klucz API jest wpisany, jeśli wybrana usługa go wymaga.
- [ ] Wybrany model obsługuje obrazy, jeżeli korzystasz z PDF-ów lub wycinków.
- [ ] Arkusz egzaminacyjny jest otwarty.
- [ ] Klucz odpowiedzi jest otwarty, jeżeli planujesz `Sprawdź zadanie`.
- [ ] XAMPP i MySQL działają, jeżeli wykonujesz zapytania.
- [ ] Połączenie MySQL przeszło test.
- [ ] Wiesz, czy pracujesz tylko na szkicu, czy również zapisałeś pliki przez `Zapisz bieżący plik`.

## 12. Aktualizowanie manuala

Manual należy aktualizować razem z aplikacją. Obowiązkowy przegląd dokumentu wykonaj po zmianie:

- nazwy instalatora, sposobu instalacji albo skrótów;
- menu, nazw przycisków, pól i komunikatów;
- listy providerów, modeli lub domyślnych adresów API;
- wymagań dotyczących kluczy i modeli vision;
- sposobu otwierania i przetwarzania PDF-ów;
- połączenia z MySQL, edytorów albo skrótów SQL;
- autosave, zapisu plików, historii rozmów lub wyników oceniania;
- formatu raportu i warunków działania `Sprawdź zadanie`;
- listy typowych problemów i sposobów ich rozwiązania.

Po każdej takiej zmianie sprawdź instrukcję na działającej wersji aplikacji i zaktualizuj numer wersji manuala na początku pliku.
