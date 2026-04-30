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
    "konferencje stomatologiczne 2025",
    "kursy dla dentystow Polska",
    "szkolenia stomatologiczne online",
    "punkty edukacyjne NIL dentysta",
    "kongres implantologiczny Polska",
    "kurs endodoncji z mikroskopem",
    "szkolenia periodontologiczne Polska",
    "konferencje ortodontyczne 2025 2026",
    "kurs chirurgii implantologicznej",
    "stomatologia estetyczna szkolenia",
    "alignery kurs kliniczny",
    "licowki ceramiczne szkolenie",
    "cyfrowa stomatologia CAD CAM kurs",
    "CBCT stomatologia kurs interpretacji",
    "sedacja wziewna kurs certyfikat",
    "protetyka na implantach szkolenie",
    "konferencje dla technikow dentystycznych",
    "Digital Smile Design kurs Polska",
    "wybielanie zebow szkolenie",
    "leczenie endodontyczne retreatment kurs",
    "pedodoncja szkolenia dla dentystow",
    "konferencja periodontologiczna Polska",
    "regeneracja kosci szkolenie GBR",
    "sinus lift kurs chirurgiczny",
    "okluzja i protezy szkolenia",
    "ortodoncja dorosli kurs kliniczny",
    "mikrobiom jamy ustnej konferencja",
    "profilaktyka prochnicy kurs dla dentystow",
    "zarządzanie gabinetem stomatologicznym szkolenie",
    "komunikacja z pacjentem stomatologia kurs",
    # --- kolejne 30 fraz ---
    "konferencje stomatologiczne Warszawa",
    "konferencje stomatologiczne Krakow",
    "CEDE targi stomatologiczne Poznan",
    "KRAKDENT kongres stomatologiczny",
    "kurs augmentacji kosci dentysta",
    "implanty natychmiastowe protokol kliniczny",
    "All-on-4 All-on-6 kurs implantologia",
    "chirurgia plastyczna dziasel kurs",
    "recesje dziasel leczenie szkolenie",
    "periimplantitis leczenie konferencja",
    "planowanie implantow CBCT tomografia",
    "robotyka cyfrowa stomatologia konferencja",
    "sztuczna inteligencja AI stomatologia szkolenie",
    "szablony chirurgiczne druk 3D implantologia",
    "skaner wewnatrzustny wycisk cyfrowy kurs",
    "ceramika cyrkonowa zirconia szkolenie",
    "kompozyt bezposredni kurs kliniczny",
    "techniki klejenia bonding szkolenie stomatologia",
    "sedacja podtlenkiem azotu dzieci kurs",
    "stomatologia biologiczna holistyczna konferencja",
    "bruksizm zgrzytanie zebami leczenie kurs",
    "aparat ortodontyczny Damon szkolenie",
    "Invisalign kurs kliniczny Polska",
    "retencja ortodontyczna szkolenie dentysta",
    "estetyka usmiechu planowanie szkolenie",
    "fotografia stomatologiczna kurs podstawy",
    "marketing gabinetu stomatologicznego szkolenie",
    "prawo medyczne dla dentystow kurs",
    "dokumentacja medyczna gabinet stomatologiczny",
    "wypalenie zawodowe dentysta wellbeing konferencja",
    # --- kolejne 30 fraz ---
    "konferencje stomatologiczne Gdansk Trojmiasto",
    "konferencje stomatologiczne Wroclaw",
    "konferencje stomatologiczne Poznan",
    "konferencja stomatologiczna Lodz",
    "zjazd polskiego towarzystwa stomatologicznego",
    "kongres PTS stomatologia Polska",
    "kurs endodoncji rotacyjne NiTi systemy",
    "WaveOne Reciproc ProTaper szkolenie kurs",
    "obturacja termoplastyczna kurs endodoncja",
    "mikroskop operacyjny ergonomia kurs",
    "leczenie kanalowe zeba mlecznego kurs",
    "pulpotomia zab mleczny szkolenie pedodoncja",
    "lakowanie zebow profilaktyka kurs dentysta",
    "fluorkowanie profilaktyka prochnica szkolenie",
    "osteoresorpcja implanty biologia szkolenie",
    "platelet rich fibrin PRF kurs implantologia",
    "protezy calkowite bezzebna szeka kurs",
    "overdenture protezy na implantach kurs",
    "most na implantach protetyka kurs kliniczny",
    "ceramika IPS emax szkolenie technik dentysta",
    "kurs gipsowania artykulatora okluzja",
    "rejestracja relacji zebrowej kurs protetyka",
    "leczenie wad szkieletowych ortodoncja chirurgia",
    "ekspansja luku ortodontia kurs dzieci",
    "myofunkcjonalna terapia ortodoncja szkolenie",
    "hipnoza dentysta leczenie leku kurs",
    "komunikacja trudny pacjent stomatologia kurs",
    "praca pod lupami powiekszenie stomatologia",
    "ergonomia pracy dentysta zapobieganie urazom",
    "ubezpieczenia OC dentysta odpowiedzialnosc szkolenie",
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

    prompt = f"""Jestes ekspertem SEO i specjalista ds. stomatologii. Napisz artykul blogowy dla portalu gdzie-konferencje.pl.

Portal agreguje konferencje, kursy i szkolenia stomatologiczne w Polsce. Czytelnicy to lekarze dentysci, technicy dentystyczni i pracownicy branzy medycznej.

FRAZA KLUCZOWA do targetowania: "{keyword}"
Fraza musi pojawic sie naturalnie w: tytule, opisie SEO, pierwszym akapicie i przynajmniej jednym naglowku H2.

Istniejace artykuly (NIE powtarzaj tematow):
{existing_list}

Wymogi artykulu:
1. Minimum 700 slow merytorycznej tresci po polsku
2. Poprawne polskie znaki diakrytyczne (ą, ę, ó, ś, ź, ż, ć, ń, ł)
3. BEZ myslnikow em (—) - uzywaj zwyklego (-)
4. BEZ emoji
5. Struktura: wstep (fraza kluczowa w 1. akapicie), 4-6 sekcji z naglowkami ##, podsumowanie
6. Praktyczne, merytoryczne informacje - nie marketingowy jezyk
7. Gdzie naturalne - wspominaj o konferencjach i szkoleniach w Polsce

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
        model="claude-3-5-sonnet-20241022",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    # Usun ewentualny markdown code block
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Niepoprawny JSON od Claude: {e}")
        print("Odpowiedz:", raw[:500])
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
