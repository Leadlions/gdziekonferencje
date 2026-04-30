"""
Skrypt generujacy artykuly blogowe dla gdzie-konferencje.pl
- Analizuje istniejace artykuly
- Wybiera nieuzyta fraze kluczowa z listy SEO
- Generuje artykul zoptymalizowany pod te fraze
- Zapisuje jako MDX
"""

import os
import re
import json
import random
from pathlib import Path
from datetime import date
import anthropic

# ---------------------------------------------------------------------------
# Lista docelowych fraz kluczowych SEO
# Skrypt wybiera kolejna nieobslugiwana fraze z tej listy
# ---------------------------------------------------------------------------
TARGET_KEYWORDS = [
    # --- Kongresy, targi, zjazdy ---
    "konferencje stomatologiczne 2025",
    "kursy dla dentystow Polska",
    "szkolenia stomatologiczne online",
    "punkty edukacyjne NIL dentysta",
    "kongres implantologiczny Polska",
    "konferencje ortodontyczne 2025 2026",
    "konferencje dla technikow dentystycznych",
    "konferencja periodontologiczna Polska",
    "konferencje stomatologiczne Warszawa",
    "konferencje stomatologiczne Krakow",
    "CEDE targi stomatologiczne Poznan",
    "KRAKDENT kongres stomatologiczny",
    "konferencje stomatologiczne Gdansk Trojmiasto",
    "konferencje stomatologiczne Wroclaw",
    "konferencje stomatologiczne Poznan",
    "konferencja stomatologiczna Lodz",
    "zjazd polskiego towarzystwa stomatologicznego",
    "kongres PTS stomatologia Polska",
    # --- Szkolenia i kursy (tematyczne - BEZ protokolow klinicznych) ---
    "szkolenia periodontologiczne Polska",
    "kurs endodoncji z mikroskopem",
    "kurs chirurgii implantologicznej",
    "stomatologia estetyczna szkolenia",
    "licowki ceramiczne szkolenie",
    "cyfrowa stomatologia CAD CAM kurs",
    "CBCT stomatologia kurs interpretacji",
    "protetyka na implantach szkolenie",
    "Digital Smile Design kurs Polska",
    "pedodoncja szkolenia dla dentystow",
    "mikrobiom jamy ustnej konferencja",
    "planowanie implantow CBCT tomografia",
    "robotyka cyfrowa stomatologia konferencja",
    "sztuczna inteligencja AI stomatologia szkolenie",
    "szablony chirurgiczne druk 3D implantologia",
    "skaner wewnatrzustny wycisk cyfrowy kurs",
    "ceramika cyrkonowa zirconia szkolenie",
    "stomatologia biologiczna holistyczna konferencja",
    "aparat ortodontyczny Damon szkolenie",
    "Invisalign szkolenia Polska",
    "estetyka usmiechu planowanie szkolenie",
    "fotografia stomatologiczna kurs podstawy",
    "kurs endodoncji rotacyjne NiTi systemy",
    "mikroskop operacyjny ergonomia kurs",
    "ceramika IPS emax szkolenie technik dentysta",
    "All-on-4 All-on-6 szkolenia implantologia",
    "augmentacja kosci kurs implantologia",
    "chirurgia plastyczna dziasel kurs",
    "periimplantitis konferencja szkolenie",
    "regeneracja kosci szkolenie GBR",
    "platelet rich fibrin PRF kurs implantologia",
    "protezy calkowite bezzebna szeka kurs",
    "overdenture protezy na implantach kurs",
    "protetyka most na implantach kurs",
    "kurs gipsowania artykulatora okluzja",
    "leczenie wad szkieletowych ortodoncja chirurgia",
    "myofunkcjonalna terapia ortodoncja szkolenie",
    # --- Biznes, prawo, zarzadzanie ---
    "marketing gabinetu stomatologicznego szkolenie",
    "prawo medyczne dla dentystow kurs",
    "dokumentacja medyczna gabinet stomatologiczny",
    "wypalenie zawodowe dentysta wellbeing konferencja",
    "zarządzanie gabinetem stomatologicznym szkolenie",
    "komunikacja z pacjentem stomatologia kurs",
    "ubezpieczenia OC dentysta odpowiedzialnosc szkolenie",
    "ergonomia pracy dentysta zapobieganie urazom",
    "praca pod lupami powiekszenie stomatologia",
    "komunikacja trudny pacjent stomatologia kurs",
    # --- Technologie i rynek ---
    "sztuczna inteligencja AI radiologia stomatologiczna",
    "telemedycyna stomatologia konferencja",
    "rynek stomatologiczny Polska trendy 2025",
    "druk 3D protetyka stomatologia szkolenie",
    "cyfrowy workflow stomatologia integracja",
    "ekologia gabinet stomatologiczny zrownowazone praktyki",
    "finansowanie kursow dentystycznych dofinansowanie",
    "akredytacja szkolenia stomatologiczne Polska",
    "wybor kursu stomatologicznego jak ocenic jakosc",
    "networking stomatologia konferencje korzyści",
]

# ---------------------------------------------------------------------------
# Pomocnicze funkcje
# ---------------------------------------------------------------------------

def read_existing_articles(blog_dir: Path) -> tuple[list[str], list[str]]:
    """Zwraca liste istniejacych tytulow i slugow."""
    titles = []
    slugs = []
    for mdx_file in blog_dir.glob("*.mdx"):
        slugs.append(mdx_file.stem)
        content = mdx_file.read_text(encoding="utf-8")
        m = re.search(r'^title:\s*["\'](.+?)["\']', content, re.MULTILINE)
        if m:
            titles.append(m.group(1))
    return titles, slugs


def pick_keyword(existing_titles: list[str], existing_slugs: list[str]) -> str:
    """Wybiera fraze kluczowa ktorej jeszcze nie ma w artykule."""
    def normalize(s: str) -> str:
        return s.lower().replace("-", " ")

    covered = [normalize(t) for t in existing_titles + existing_slugs]

    unused = []
    for kw in TARGET_KEYWORDS:
        kw_norm = normalize(kw)
        already_covered = any(kw_norm in c or c in kw_norm for c in covered)
        if not already_covered:
            unused.append(kw)

    if unused:
        return random.choice(unused)

    # Wszystkie frazy uzyte - losuj dowolna (i tak bedzie nowy artykul)
    return random.choice(TARGET_KEYWORDS)


def slugify(text: str) -> str:
    """Zamienia tekst na slug URL-friendly."""
    replacements = {
        'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
        'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
        'Ą': 'a', 'Ć': 'c', 'Ę': 'e', 'Ł': 'l', 'Ń': 'n',
        'Ó': 'o', 'Ś': 's', 'Ź': 'z', 'Ż': 'z',
    }
    for pl, ascii_char in replacements.items():
        text = text.replace(pl, ascii_char)
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text


# ---------------------------------------------------------------------------
# Glowna logika
# ---------------------------------------------------------------------------

def main():
    blog_dir = Path("src/content/blog")
    if not blog_dir.exists():
        print("ERROR: Nie znaleziono folderu src/content/blog")
        raise SystemExit(1)

    existing_titles, existing_slugs = read_existing_articles(blog_dir)
    keyword = pick_keyword(existing_titles, existing_slugs)
    print(f"Wybrana fraza kluczowa: {keyword}")
    print(f"Istniejace artykuly: {len(existing_titles)}")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    existing_list = "\n".join(f"- {t}" for t in existing_titles) if existing_titles else "(brak)"

    prompt = f"""Jestes redaktorem portalu gdzie-konferencje.pl i specjalista SEO. Napisz artykul blogowy dla tego portalu.

Portal agreguje konferencje, kursy i szkolenia stomatologiczne w Polsce. Czytelnicy to lekarze dentysci, technicy dentystyczni i pracownicy branzy medycznej szukajacy informacji o wydarzeniach branżowych, szkoleniach i rynku stomatologicznym.

FRAZA KLUCZOWA do targetowania: "{keyword}"
Fraza musi pojawic sie naturalnie w: tytule, opisie SEO, pierwszym akapicie i przynajmniej jednym naglowku H2.

Istniejace artykuly (NIE powtarzaj tematow):
{existing_list}

BEZWZGLEDNY ZAKAZ - tego NIE wolno pisac:
- Zadnych protokolow klinicznych leczenia (np. "protokol leczenia choroby przyzebia")
- Zadnych wskazan ani przeciwwskazan terapeutycznych
- Zadnych informacji o dawkowaniu lekow, materialow, substancji
- Zadnych porad "jak leczyc pacjenta z..."
- Zadnych instrukcji klinicznych krok po kroku
Artykul ma dotyczyc WYDARZEN (konferencji, kursow, szkolen), RYNKU, KARIERY, TECHNOLOGII - nie protokolow medycznych.

Wymogi artykulu:
1. Minimum 700 slow merytorycznej tresci po polsku
2. Poprawne polskie znaki diakrytyczne (ą, ę, ó, ś, ź, ż, ć, ń, ł)
3. BEZ myslnikow em (—) - uzywaj zwyklego (-)
4. BEZ emoji
5. Struktura: wstep (fraza kluczowa w 1. akapicie), 4-6 sekcji z naglowkami ##, podsumowanie
6. Praktyczne, merytoryczne informacje o branzy - nie marketingowy jezyk
7. Gdzie naturalne - podawaj konkretne przykłady konferencji i szkolen w Polsce (nazwy towarzystw, miast, dat)

ZASADY ANTY-AI (kluczowe - nie lazem ich):
- NIE uzywaj zwrotow: "w dzisiejszych czasach", "warto zaznaczyc", "nalezy podkreslic", "bez watpienia", "co wiecej", "podsumowujac powyzsze", "w konkluzji"
- NIE zacznaj zdan od: "Dodatkowo,", "Ponadto,", "Co wiecej,", "Niemniej jednak,"
- NIE pisz kazdej sekcji wedlug schematu: zdanie + lista punktowana. Mieszaj - czasem lista, czasem czysty tekst, czasem krotki akapit
- NIE uzywaj pustych otwieraczy akapitu ("Jest to wazne poniewaz...", "Warto zwrocic uwage...")
- UZYWAJ konkretnych przykladow, liczb, nazw towarzystw, tytulow kursow - nie ogolnikow
- PISZ jak praktyk do praktyka - bezposrednio, konkretnie, bez owijania w bawelne
- Roznicuj dlugosci zdan: krotkie i dlugie naprzemiennie
- Mozesz zadawac pytania retoryczne - to naturalizuje tekst
- Unikaj symetrii - nie kazda sekcja musi miec taka sama strukture

Odpowiedz WYLACZNIE w formacie JSON (bez markdown code block, bez komentarzy):
{{
  "title": "Tytul artykulu zawierajacy fraze kluczowa",
  "description": "Opis SEO 150-160 znakow zawierajacy fraze kluczowa",
  "slug": "slug-url-bez-polskich-znakow-z-myslnikami",
  "tags": ["tag1", "tag2", "tag3"],
  "content": "Pelna tresc artykulu w formacie Markdown (naglowki ##, akapity, listy)"
}}"""

    print("Generowanie artykulu przez Claude API...")
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    print(f"Odpowiedz Claude ({len(raw)} znakow)")

    # Usun ewentualny markdown code block (rozne warianty)
    raw = re.sub(r'^```json\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'^```\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'```\s*$', '', raw, flags=re.MULTILINE)
    raw = raw.strip()

    # Znajdz pierwszy { i ostatni } zeby wyciagnac sam JSON
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1:
        raw = raw[start:end+1]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Niepoprawny JSON od Claude: {e}")
        print("Pierwsze 800 znakow odpowiedzi:")
        print(raw[:800])
        raise SystemExit(1)

    # Buduj slug
    slug = slugify(data.get("slug", data["title"]))
    if slug in existing_slugs:
        slug = f"{slug}-{date.today().strftime('%Y%m%d')}"

    # Buduj frontmatter
    today = date.today().isoformat()
    tags = data.get("tags", ["stomatologia", "szkolenia"])
    tags_str = ", ".join(f'"{t}"' for t in tags)

    mdx_content = f"""---
title: "{data['title']}"
description: "{data['description']}"
publishedAt: {today}
tags: [{tags_str}]
author: "Redakcja gdzie-konferencje.pl"
---

{data['content']}
"""

    output_path = blog_dir / f"{slug}.mdx"
    output_path.write_text(mdx_content, encoding="utf-8")
    print(f"Zapisano: {output_path}")
    print(f"Tytul: {data['title']}")
    print(f"Slug: {slug}")


if __name__ == "__main__":
    main()
