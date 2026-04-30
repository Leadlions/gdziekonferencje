"""
Miesieczny skrypt aktualizujacy konferencje dla gdzie-konferencje.pl
- Pobiera strony towarzystw stomatologicznych
- Uzywa Claude API do wyciagniecia danych o konferencjach
- Deduplikuje i merguje z istniejacym conferences.json
"""

import os
import json
import re
import requests
from pathlib import Path
import anthropic

# ---------------------------------------------------------------------------
# Zrodla do przeszukania
# ---------------------------------------------------------------------------
SOURCES = [
    {"name": "PTS", "url": "https://pts.net.pl/kongresy-i-konferencje/"},
    {"name": "PSI", "url": "https://psi-icoi.pl/kongresy"},
    {"name": "PTO", "url": "https://pto.net.pl/aktualnosci/"},
    {"name": "KRAKDENT", "url": "https://krakdent.pl/"},
    {"name": "CEDE", "url": "https://www.cede.pl/"},
    {"name": "DENTOPOLIS", "url": "https://kwintesencja.com.pl/konferencje/"},
    {"name": "Asysdent", "url": "https://www.asysdent.pl/"},
    {"name": "PASE", "url": "https://pase.org.pl/"},
    {"name": "PTSL", "url": "https://ptsl.com.pl/events/"},
    {"name": "PTDNŻ", "url": "https://dysfunkcje.pl/"},
    {"name": "OIL Warszawa", "url": "https://izba-lekarska.pl/doskonalenie-zawodowe/"},
    {"name": "NIL", "url": "https://nil.org.pl/dla-lekarzy/dla-stomatologow"},
    {"name": "DentalTutor", "url": "https://dentaltutor.pl/"},
    {"name": "Denon Dental", "url": "https://kongres.dental.pl/"},
]

VALID_SLUGS = [
    "stomatologia",
    "implantologia",
    "protetyka",
    "stomatologia-estetyczna",
    "ortodoncja",
    "chirurgia-stomatologiczna",
    "periodontologia",
    "endodoncja",
    "stomatologia-dziecieca",
]

CONFERENCES_PATH = Path("src/data/conferences.json")

# ---------------------------------------------------------------------------
# Funkcje pomocnicze
# ---------------------------------------------------------------------------

def fetch_page(url: str) -> str:
    """Pobiera HTML strony. Zwraca pusty string jesli blad."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; gdzie-konferencje-bot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        # Ogranicz do 15000 znakow zeby nie przekroczyc limitu tokenow
        return resp.text[:15000]
    except Exception as e:
        print(f"  BLAD pobierania {url}: {e}")
        return ""


def extract_conferences(client: anthropic.Anthropic, source: dict, html: str) -> list[dict]:
    """Uzywa Claude API do wyciagniecia konferencji z HTML."""
    if not html:
        return []

    prompt = f"""Przeanalizuj ponizszy HTML ze strony {source['name']} ({source['url']}) i wyciagnij wszystkie konferencje, kongresy, kursy i szkolenia stomatologiczne na rok 2025 i 2026.

Dla kazdego zdarzenia zwroc JSON z polami:
- name: pelna nazwa konferencji
- date: data w formacie "DD-DD miesiac RRRR" lub "DD miesiac RRRR" (po polsku, np. "15-17 maja 2026")
- city: miasto i miejsce jesli znane
- specialty: krótki opis specjalizacji
- slugs: tablica z pasujacymi slugami sposrod: {VALID_SLUGS}
- organizer: nazwa organizatora
- url: link do strony konferencji (jesli jest w HTML, inaczej {source['url']})

Odpowiedz TYLKO tablicą JSON (bez markdown, bez komentarzy). Jesli nie ma konferencji na 2025-2026, zwroc [].

HTML:
{html}"""

    try:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"  BLAD parsowania odpowiedzi Claude: {e}")
        return []


def normalize_name(name: str) -> str:
    """Normalizuje nazwe konferencji do porownania (deduplikacja)."""
    return re.sub(r'\s+', ' ', name.lower().strip())


def merge_conferences(existing: list[dict], new_items: list[dict]) -> tuple[list[dict], int]:
    """Merguje nowe konferencje z istniejacymi. Zwraca polaczona liste i liczbe dodanych."""
    existing_names = {normalize_name(c["name"]) for c in existing}
    added = 0

    for item in new_items:
        if not item.get("name") or not item.get("date"):
            continue
        # Walidacja slugow
        item["slugs"] = [s for s in item.get("slugs", []) if s in VALID_SLUGS]
        if not item["slugs"]:
            item["slugs"] = ["stomatologia"]

        norm = normalize_name(item["name"])
        if norm not in existing_names:
            existing.append(item)
            existing_names.add(norm)
            added += 1
            print(f"  + Dodano: {item['name']}")

    return existing, added


# ---------------------------------------------------------------------------
# Glowna logika
# ---------------------------------------------------------------------------

def main():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Wczytaj istniejace konferencje
    existing = json.loads(CONFERENCES_PATH.read_text(encoding="utf-8"))
    print(f"Istniejace konferencje: {len(existing)}")

    total_added = 0

    for source in SOURCES:
        print(f"\nPobieranie: {source['name']} ({source['url']})")
        html = fetch_page(source["url"])
        if not html:
            continue

        conferences = extract_conferences(client, source, html)
        print(f"  Znalezione: {len(conferences)}")

        existing, added = merge_conferences(existing, conferences)
        total_added += added

    print(f"\nLacznie dodano: {total_added} nowych konferencji")
    print(f"Lacznie w bazie: {len(existing)} konferencji")

    # Zapisz zaktualizowany plik
    CONFERENCES_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Zapisano: {CONFERENCES_PATH}")


if __name__ == "__main__":
    main()
