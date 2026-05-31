# Opis projektu

## Tytuł

**Analiza dostępności aptek w Lublinie z wykorzystaniem GIS**

## Postawienie problemu

Dostęp do aptek jest ważnym elementem infrastruktury miejskiej. Apteki zapewniają mieszkańcom dostęp do leków, podstawowych produktów zdrowotnych oraz konsultacji farmaceutycznych. Ich rozmieszczenie przestrzenne może wpływać na komfort i bezpieczeństwo mieszkańców, szczególnie osób starszych, osób z niepełnosprawnościami oraz mieszkańców obszarów peryferyjnych.

Głównym problemem analizowanym w projekcie jest sprawdzenie, czy apteki w Lublinie są rozmieszczone równomiernie oraz czy mieszkańcy różnych dzielnic mają podobny dostęp przestrzenny do aptek.

Główne pytanie badawcze brzmi:

**Czy mieszkańcy różnych dzielnic Lublina mają podobny dostęp do aptek?**

## Dotychczasowe podejścia

Dostępność przestrzenna jest często analizowana z wykorzystaniem metod GIS. W analizach miejskich dostępność usług można badać między innymi przez:

- liczenie liczby punktów usługowych w jednostkach administracyjnych,
- obliczanie gęstości usług na kilometr kwadratowy,
- mierzenie odległości do najbliższego punktu usługowego,
- tworzenie stref buforowych wokół punktów usługowych,
- analizowanie procentowego pokrycia obszaru przez strefy dostępności.

W tym projekcie analiza opiera się na lokalizacjach aptek oraz granicach dzielnic Lublina. Wykorzystano operacje spatial join, obliczenia powierzchni, analizę gęstości oraz analizę buforową.

## Dane wykorzystane w projekcie

W projekcie wykorzystano dwa główne typy danych przestrzennych.

### 1. Lokalizacje aptek

Lokalizacje aptek zostały pobrane z OpenStreetMap. Wybrano obiekty oznaczone tagiem:

```text
amenity=pharmacy
```

Pobrane dane zostały zapisane w formatach GeoJSON oraz CSV.

### 2. Granice dzielnic Lublina

Granice dzielnic zostały pobrane z oficjalnego serwisu danych przestrzennych miasta Lublin. Oryginalne dane były dostępne w formacie SHP. Początkowy układ współrzędnych danych to `EPSG:2179`.

Do analizy wszystkie warstwy przestrzenne zostały przekształcone do układu `EPSG:2180`, który umożliwia poprawne obliczanie odległości, powierzchni i buforów w metrach.

## Zaproponowane podejście

Projekt został wykonany w kilku etapach.

### 1. Pobranie danych

W pierwszym etapie pobrano granicę Lublina oraz lokalizacje aptek z OpenStreetMap. Następnie pobrano granice dzielnic Lublina z oficjalnego źródła danych przestrzennych miasta.

### 2. Przygotowanie danych

Pobrane dane przestrzenne zostały oczyszczone i przygotowane do analizy. Usunięto puste geometrie, sprawdzono układy współrzędnych oraz zamieniono geometrie aptek na punkty.

Dane aptek zostały ograniczone tylko do tych obiektów, które znajdują się w granicach miasta Lublin.

### 3. Analiza według dzielnic

Każda apteka została przypisana do odpowiedniej dzielnicy za pomocą operacji spatial join. Następnie obliczono liczbę aptek w każdej dzielnicy.

Dla każdej dzielnicy obliczono następujące wskaźniki:

- powierzchnia dzielnicy w km²,
- liczba aptek,
- liczba aptek na km²,
- ranking według liczby aptek,
- ranking według gęstości aptek.

### 4. Analiza buforowa

W celu oszacowania dostępności przestrzennej utworzono bufory 500 m i 1000 m wokół aptek.

Bufor 500 m reprezentuje krótki dystans pieszy do apteki. Bufor 1000 m reprezentuje szerszą strefę dostępności.

Dla całego miasta obliczono:

- powierzchnię znajdującą się w zasięgu 500 m od apteki,
- powierzchnię poza zasięgiem 500 m od apteki,
- powierzchnię znajdującą się w zasięgu 1000 m od apteki,
- powierzchnię poza zasięgiem 1000 m od apteki.

Podobną analizę wykonano również osobno dla każdej dzielnicy.

### 5. Wizualizacja wyników

Wyniki zostały przedstawione za pomocą:

- map statycznych,
- map choropleth,
- wykresów rankingowych,
- interaktywnej mapy HTML utworzonej z wykorzystaniem biblioteki Folium.

## Najważniejsze wyniki

W analizie zidentyfikowano **136 aptek** w Lublinie.

Całkowita powierzchnia miasta wynosi około **147,47 km²**.

Średnia gęstość aptek w mieście wynosi około **0,92 apteki/km²**.

Dzielnicą z największą liczbą aptek jest **Śródmieście**, gdzie znajduje się **21 aptek**.

Dzielnice, w których w analizowanym zbiorze danych nie znaleziono aptek, to:

- Hajdów - Zadębie,
- Szerokie,
- Węglin Płn.

Analiza bufora 500 m wykazała, że **31,71% powierzchni miasta** znajduje się w odległości do 500 m od apteki.

Analiza bufora 1000 m wykazała, że **56,41% powierzchni miasta** znajduje się w odległości do 1000 m od apteki.

## Interpretacja wyników

Wyniki wskazują, że apteki w Lublinie nie są rozmieszczone równomiernie. Dzielnice centralne i bardziej zurbanizowane mają lepszy dostęp do aptek, natomiast dzielnice peryferyjne charakteryzują się słabszą dostępnością.

Dzielnice takie jak Śródmieście, Rury, Czuby Płn. i Wieniawa mają dużą liczbę aptek oraz stosunkowo wysoką gęstość aptek.

Dzielnice peryferyjne, takie jak Hajdów - Zadębie, Szerokie, Abramowice i Zemborzyce, mają wyraźnie niższą dostępność według analizy buforowej.

## Ograniczenia

W projekcie wykorzystano odległość euklidesową. Oznacza to, że odległość jest liczona w linii prostej i nie uwzględnia rzeczywistej sieci ulic, przejść dla pieszych, tras komunikacji miejskiej ani barier przestrzennych.

Drugim ograniczeniem jest wykorzystanie danych z OpenStreetMap. Jest to wartościowe źródło otwartych danych, ale może zawierać braki lub nieaktualne informacje.

Analiza skupia się wyłącznie na dostępności przestrzennej. Nie uwzględnia godzin otwarcia aptek, wielkości aptek, dostępności konkretnych leków ani liczby mieszkańców w poszczególnych dzielnicach.

## Możliwe kierunki rozwoju projektu

Projekt można rozszerzyć przez:

- dodanie danych o liczbie mieszkańców w każdej dzielnicy,
- obliczenie liczby aptek na 10 000 mieszkańców,
- wykorzystanie rzeczywistych tras pieszych zamiast buforów euklidesowych,
- analizę dostępności aptek z wykorzystaniem komunikacji miejskiej,
- uwzględnienie godzin otwarcia aptek,
- porównanie dostępności aptek z dostępnością innych usług, na przykład przychodni lub szpitali.