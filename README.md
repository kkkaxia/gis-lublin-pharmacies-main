# Analiza dostępności aptek w Lublinie z wykorzystaniem GIS

Projekt dotyczy analizy przestrzennej dostępności aptek w Lublinie z wykorzystaniem metod GIS oraz otwartych danych przestrzennych.

Głównym celem projektu jest sprawdzenie, jak apteki są rozmieszczone w dzielnicach Lublina oraz które części miasta mają lepszy lub gorszy dostęp do aptek.

## Temat projektu

**GIS — analiza danych przestrzennych**

## Pytanie badawcze

Czy mieszkańcy różnych dzielnic Lublina mają podobny dostęp przestrzenny do aptek?

## Główne cele projektu

- Pobranie lokalizacji aptek z OpenStreetMap.
- Pobranie granic administracyjnych dzielnic Lublina.
- Przygotowanie i oczyszczenie danych przestrzennych.
- Przypisanie aptek do dzielnic za pomocą operacji spatial join.
- Obliczenie liczby aptek w każdej dzielnicy.
- Obliczenie gęstości aptek na kilometr kwadratowy.
- Utworzenie buforów 500 m i 1000 m wokół aptek.
- Analiza obszarów znajdujących się w zasięgu aptek.
- Wizualizacja wyników za pomocą map statycznych, wykresów oraz interaktywnej mapy HTML.

## Technologie

Projekt został wykonany w języku Python z wykorzystaniem bibliotek:

- GeoPandas
- Pandas
- OSMnx
- Shapely
- Matplotlib
- Folium
- Branca

## Struktura projektu

```text
gis-lublin-pharmacies/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── maps/
│
├── src/
│   ├── download_data.py
│   ├── preprocess.py
│   ├── download_districts.py
│   ├── analyze_districts.py
│   ├── buffer_analysis.py
│   └── create_interactive_map.py
│
├── tables/
│
├── README.md
├── DESC.md
├── EXAMPLE.md
├── requirements.txt
└── .gitignore
```

## Źródła danych

W projekcie wykorzystano dwa główne źródła danych.

### 1. OpenStreetMap

Lokalizacje aptek zostały pobrane z OpenStreetMap za pomocą biblioteki OSMnx. Wybrane zostały obiekty oznaczone tagiem:

```text
amenity=pharmacy
```

### 2. Otwarte dane przestrzenne miasta Lublin

Granice dzielnic Lublina zostały pobrane z oficjalnego serwisu danych przestrzennych miasta Lublin w formacie SHP.

## Układy współrzędnych

W projekcie wykorzystano kilka układów współrzędnych:

- `EPSG:4326` — układ geograficzny używany do zapisu i wyświetlania danych na mapach internetowych.
- `EPSG:2179` — oryginalny układ współrzędnych pliku SHP z granicami dzielnic.
- `EPSG:2180` — układ płaski używany do obliczania odległości, powierzchni i buforów w metrach.

## Instalacja

Najpierw należy utworzyć środowisko wirtualne:

```bash
python -m venv .venv
```

Następnie aktywować środowisko w Windows PowerShell:

```bash
.venv\Scripts\activate
```

Potem należy zainstalować wymagane biblioteki:

```bash
pip install -r requirements.txt
```

## Uruchomienie projektu

Skrypty należy uruchamiać w podanej kolejności:

```bash
python src/download_data.py
python src/preprocess.py
python src/download_districts.py
python src/analyze_districts.py
python src/buffer_analysis.py
python src/create_interactive_map.py
```

## Pliki wynikowe

Projekt generuje kilka typów plików wynikowych.

### Tabele

```text
tables/district_pharmacy_stats.csv
tables/pharmacies_with_districts.csv
tables/district_buffer_coverage_stats.csv
```

### Mapy statyczne i wykresy

```text
maps/pharmacies_count_by_district.png
maps/pharmacies_density_by_district.png
maps/pharmacies_and_districts.png
maps/pharmacy_ranking_by_district.png
maps/pharmacy_density_ranking.png
maps/pharmacy_buffer_500m_map.png
maps/pharmacy_buffer_1000m_map.png
maps/pharmacy_uncovered_500m_map.png
maps/district_coverage_500m_map.png
maps/district_coverage_1000m_map.png
maps/district_buffer_coverage_chart.png
```

### Mapa interaktywna

```text
maps/lublin_pharmacies_interactive_map.html
```

Ten plik można otworzyć w przeglądarce internetowej.

## Najważniejsze wyniki

W analizie zidentyfikowano **136 aptek** w Lublinie.

Całkowita powierzchnia Lublina wynosi około **147,47 km²**.

Średnia gęstość aptek dla całego miasta wynosi około **0,92 apteki/km²**.

Analiza bufora 500 m wykazała, że **31,71% powierzchni miasta** znajduje się w odległości do 500 m od apteki.

Analiza bufora 1000 m wykazała, że **56,41% powierzchni miasta** znajduje się w odległości do 1000 m od apteki.

## Ograniczenia analizy

Analiza buforowa została wykonana na podstawie odległości euklidesowej. Oznacza to, że odległość liczona jest w linii prostej, a nie po rzeczywistej sieci ulic lub chodników.

Dane z OpenStreetMap mogą być niepełne lub zawierać drobne nieścisłości, ponieważ są tworzone i aktualizowane przez społeczność użytkowników.