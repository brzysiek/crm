import re

from database import get_db
from models.crm_notes import log_history


def _normalize_word(word: str) -> str:
    letters = [c for c in word if c.isalpha()]
    if not letters:
        return word
    if all(c.isupper() for c in letters):
        return word
    out, capitalized = [], False
    for c in word:
        if not c.isalpha():
            out.append(c)
        elif not capitalized:
            out.append(c.upper())
            capitalized = True
        else:
            out.append(c.lower())
    return ''.join(out)


def _split_compound(token: str) -> list[str]:
    """Rozbija złożenia po / i -, żeby każdy człon oceniać osobno: w „IT/Edukacja"
    pierwszy człon jest akronimem, drugi zwykłym słowem."""
    return re.split(r'([/-])', token)


def _has_own_capital(word: str) -> bool:
    """Czy słowo samo w sobie niesie wielką literę — akronim (BNI, M&A, SaaS),
    marka (eCommerce, myTherapy) albo nazwa własna. Takiego słowa nie ruszamy,
    bo podniesienie pierwszej litery zrobiłoby z „eCommerce" → „ECommerce"."""
    return any(c.isupper() for c in word)


def capitalize_first(name: str) -> str:
    """Pierwsza litera całej nazwy z wielkiej, reszta dokładnie tak, jak wpisał
    użytkownik. „fundusze inwestycyjne" -> „Fundusze inwestycyjne",
    „Business Mixer Katowice" zostaje bez zmian.

    Po co tylko tyle: słownik tagów i branż rósł z trzech źródeł (formularz,
    wizytówki, import) i ta sama branża trafiała na listę raz z wielkiej, raz
    z małej litery. Dalej idąca normalizacja (każde kolejne słowo z małej)
    psuła nazwy własne — „Rafał Wiśniewski" stawał się „Rafał wiśniewski" —
    a tego z nazwy nie da się odróżnić od zwykłego słowa."""
    name = ' '.join(name.split())
    if not name:
        return name
    first_word = name.split(' ', 1)[0]
    if _has_own_capital(first_word):
        return name
    for i, c in enumerate(name):
        if c.isalpha():
            return name[:i] + c.upper() + name[i + 1:]
    return name


def title_case_name(name: str) -> str:
    """Każde słowo z wielkiej litery, akronimy bez zmian. Zapis dla źródeł —
    tam wartością jest zwykle imię i nazwisko osoby polecającej („Ada Hurbol"),
    więc zdaniowa normalizacja robiłaby z nazwiska małą literę."""
    def norm_compound(token: str) -> str:
        return ''.join(p if p in ('/', '-') else _normalize_word(p)
                       for p in _split_compound(token))
    return ' '.join(norm_compound(w) for w in name.split())


def normalize_tag_name(name: str, kind: str = 'tag') -> str:
    """Jedno wejście dla wszystkich zapisów wartości słownikowych. Źródła trzymają
    nazwiska, więc zostają przy zapisie tytułowym; tagi, branże i tagi email
    (zgody marketingowe) dostają tylko wielką pierwszą literę."""
    return title_case_name(name) if kind == 'source' else capitalize_first(name)


def as_filter_list(value) -> list[str]:
    """Filtry przyjmują i jedną wartość, i listę — stare linki z `?tag=X` mają
    działać dalej, a nowe `?tag=X&tag=Y` znaczyć „X albo Y"."""
    if value is None or value == '':
        return []
    if isinstance(value, str):
        return [value]
    return [v for v in value if v not in (None, '')]


def company_has_tag_sql(company_col: str, kind: str, names: list[str]) -> tuple[str, list]:
    """Warunek „firma ma którąś z tych wartości" jako EXISTS, nie JOIN.

    JOIN mnożyłby wiersze przy firmie z kilkoma pasującymi wartościami i wymuszał
    DISTINCT, a przy dwóch filtrach naraz (branża ORAZ tag) robiłby z tego iloczyn.
    Kilka nazw w jednym filtrze znaczy „którakolwiek z nich" — pytanie „private
    equity albo venture capital albo family office" jest jednym pytaniem, nie trzema.
    """
    placeholders = ','.join(['%s'] * len(names))
    sql = (f"EXISTS (SELECT 1 FROM crm_company_tags _ct"
           f" JOIN crm_tags _t ON _t.id = _ct.tag_id"
           f" WHERE _ct.company_id = {company_col} AND _t.kind = %s"
           f" AND _t.name IN ({placeholders}))")
    return sql, [kind] + list(names)


def contact_has_email_tag_sql(contact_col: str, names: list[str]) -> tuple[str, list]:
    """To samo dla tagów email (zgód marketingowych), które wiszą przy kontakcie."""
    placeholders = ','.join(['%s'] * len(names))
    sql = (f"EXISTS (SELECT 1 FROM crm_contact_tags _kt"
           f" JOIN crm_tags _et ON _et.id = _kt.tag_id"
           f" WHERE _kt.contact_id = {contact_col} AND _et.kind = 'email'"
           f" AND _et.name IN ({placeholders}))")
    return sql, list(names)


def suggest_tags(kind: str, q: str = '', limit: int = 20) -> list[str]:
    """kind: 'tag' lub 'industry' — podpowiedzi istniejących nazw do tag-inputa."""
    db = get_db()
    sql = "SELECT name FROM crm_tags WHERE kind=%s"
    params = [kind]
    if q:
        sql += " AND name LIKE %s"
        params.append(f"%{q}%")
    sql += " ORDER BY name LIMIT %s"
    params.append(limit)
    with db.cursor() as cur:
        cur.execute(sql, params)
        return [r['name'] for r in cur.fetchall()]


def suggest_sources(q: str = '', limit: int = 20) -> list[dict]:
    """Podpowiedzi dla pola źródła: łączy istniejące wartości źródeł (crm_tags)
    z kontaktami pasującymi do zapytania, żeby można było wskazać osobę polecającą.
    Zwraca listę {'value': str, 'contact_id': int|None}."""
    db = get_db()
    tag_sql = "SELECT name FROM crm_tags WHERE kind='source'"
    tag_params = []
    if q:
        tag_sql += " AND name LIKE %s"
        tag_params.append(f"%{q}%")
    tag_sql += " ORDER BY name LIMIT %s"
    tag_params.append(limit)

    contact_sql = "SELECT id, first_name, last_name FROM crm_contacts WHERE archived_at IS NULL"
    contact_params = []
    if q:
        contact_sql += " AND (first_name LIKE %s OR last_name LIKE %s OR CONCAT(first_name,' ',last_name) LIKE %s)"
        like = f"%{q}%"
        contact_params.extend([like, like, like])
    contact_sql += " ORDER BY last_name, first_name LIMIT %s"
    contact_params.append(limit)

    with db.cursor() as cur:
        cur.execute(tag_sql, tag_params)
        tag_names = [r['name'] for r in cur.fetchall()]
        cur.execute(contact_sql, contact_params)
        contacts = cur.fetchall()

    results = [
        {'value': f"{c['first_name']} {c['last_name']}", 'contact_id': c['id']}
        for c in contacts
    ]
    contact_names_lower = {r['value'].lower() for r in results}
    for name in tag_names:
        if name.lower() not in contact_names_lower:
            results.append({'value': name, 'contact_id': None})

    results.sort(key=lambda r: r['value'].lower())
    return results[:limit]


def get_tags(kind: str, with_counts: bool = False) -> list[dict]:
    """with_counts dokłada company_count i contact_count — ile firm i kontaktów
    ma daną wartość przypiętą. Podzapytania zamiast JOIN-ów, bo dwa złączenia
    do tabel wiążących mnożyłyby wiersze i liczby wychodziłyby zawyżone."""
    db = get_db()
    cols = "id, name"
    if with_counts:
        cols += (", (SELECT COUNT(*) FROM crm_company_tags ct WHERE ct.tag_id = crm_tags.id)"
                 " AS company_count"
                 ", (SELECT COUNT(*) FROM crm_contact_tags kt WHERE kt.tag_id = crm_tags.id)"
                 " AS contact_count")
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {cols} FROM crm_tags WHERE kind=%s ORDER BY name", (kind,)
        )
        return cur.fetchall()


def add_tag(kind: str, name: str) -> int:
    db = get_db()
    name = normalize_tag_name(name.strip(), kind)
    try:
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO crm_tags (kind, name) VALUES (%s, %s)", (kind, name)
            )
            new_id = cur.lastrowid
        db.commit()
        return new_id
    except Exception:
        db.rollback()
        raise


def rename_tag(tag_id: int, name: str) -> None:
    """Zmienia nazwę wartości słownikowej w miejscu. Firmy, kontakty i kampanie
    wiążą się po tag_id, nie po nazwie, więc przemianowanie niczego nie odpina —
    to jedyny bezpieczny sposób na poprawienie literówki w pozycji, która jest
    już w użyciu (skasowanie i dodanie od nowa zrywa wszystkie powiązania).

    Zgłasza ValueError przy pustej nazwie i przy nazwie już zajętej w tym samym
    rodzaju — porównanie w MySQL jest bez względu na wielkość liter, więc sama
    zmiana wielkości liter („cfo" -> „CFO") przechodzi."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT kind FROM crm_tags WHERE id=%s", (tag_id,))
        row = cur.fetchone()
    if not row:
        raise ValueError('Nie ma takiej pozycji.')
    name = normalize_tag_name(name.strip(), row['kind'])
    if not name:
        raise ValueError('Nazwa nie może być pusta.')
    try:
        with db.cursor() as cur:
            cur.execute("SELECT id FROM crm_tags WHERE kind=%s AND name=%s AND id<>%s",
                        (row['kind'], name, tag_id))
            if cur.fetchone():
                raise ValueError(f'„{name}" już jest na liście.')
            cur.execute("UPDATE crm_tags SET name=%s WHERE id=%s", (name, tag_id))
        db.commit()
    except Exception:
        db.rollback()
        raise


def delete_tag(tag_id: int) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM crm_tags WHERE id=%s", (tag_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_contact_email_tags(contact_id: int) -> list[str]:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT t.name FROM crm_tags t
               JOIN crm_contact_tags ct ON ct.tag_id=t.id
               WHERE ct.contact_id=%s AND t.kind='email' ORDER BY t.name""",
            (contact_id,)
        )
        return [r['name'] for r in cur.fetchall()]


def _replace_contact_tags_of_kind(contact_id: int, kind: str, tag_ids: list[int]) -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """DELETE ct FROM crm_contact_tags ct
                   JOIN crm_tags t ON t.id = ct.tag_id
                   WHERE ct.contact_id=%s AND t.kind=%s""",
                (contact_id, kind)
            )
            for tag_id in tag_ids:
                cur.execute(
                    "INSERT IGNORE INTO crm_contact_tags (contact_id, tag_id) VALUES (%s, %s)",
                    (contact_id, tag_id)
                )
        db.commit()
    except Exception:
        db.rollback()
        raise


def set_contact_email_tags(contact_id: int, names: list[str], user_id: int | None) -> None:
    """Nadanie/odebranie tagu email jest jednocześnie udzieleniem/wycofaniem zgody
    marketingowej na dany cel komunikacji — każda zmiana trafia do historii kontaktu."""
    names = [normalize_tag_name(n.strip(), 'email') for n in names if n and n.strip()]
    current = get_contact_email_tags(contact_id)
    added = [n for n in names if n not in current]
    removed = [n for n in current if n not in names]
    tag_ids = get_or_create_tag_ids('email', names)
    _replace_contact_tags_of_kind(contact_id, 'email', tag_ids)
    for name in added:
        log_history('contact', contact_id, user_id, 'update',
                     f'Dodano tag email „{name}” (zgoda marketingowa).', entry_type='tag_add')
    for name in removed:
        log_history('contact', contact_id, user_id, 'update',
                     f'Usunięto tag email „{name}” (wycofanie zgody).', entry_type='tag_remove')


def remove_all_contact_email_tags(contact_id: int, user_id: int | None = None,
                                   reason: str = 'Wypisano z newslettera (link unsubscribe).') -> None:
    current = get_contact_email_tags(contact_id)
    if not current:
        return
    _replace_contact_tags_of_kind(contact_id, 'email', [])
    for name in current:
        log_history('contact', contact_id, user_id, 'update',
                     f'Usunięto tag email „{name}” ({reason})', entry_type='tag_remove')


def get_tag_ids_by_names(kind: str, names: list[str]) -> list[int]:
    """Jak get_or_create_tag_ids, ale nie tworzy nowych tagów — do podglądu
    (np. liczby odbiorców kampanii) zanim formularz zostanie zapisany."""
    names = [n.strip() for n in names if n and n.strip()]
    if not names:
        return []
    db = get_db()
    placeholders = ','.join(['%s'] * len(names))
    with db.cursor() as cur:
        cur.execute(
            f"SELECT id FROM crm_tags WHERE kind=%s AND name IN ({placeholders})",
            [kind] + names
        )
        return [r['id'] for r in cur.fetchall()]


def get_or_create_tag_ids(kind: str, names: list[str]) -> list[int]:
    db = get_db()
    ids = []
    try:
        with db.cursor() as cur:
            for raw_name in names:
                name = normalize_tag_name(raw_name.strip(), kind)
                if not name:
                    continue
                cur.execute(
                    "SELECT id, name FROM crm_tags WHERE kind=%s AND name=%s",
                    (kind, name)
                )
                row = cur.fetchone()
                if row:
                    # Porównanie w MySQL jest bez względu na wielkość liter, więc trafiamy
                    # tu też przy innym zapisie niż w słowniku. Zostawiamy nazwę taką, jaka
                    # jest: wpisanie „cfo" przy firmie nie ma przemianowywać wszystkim
                    # „CFO" na „Cfo". Nazwę zmienia się świadomie, w Słownikach.
                    ids.append(row['id'])
                else:
                    cur.execute(
                        "INSERT INTO crm_tags (kind, name) VALUES (%s, %s)",
                        (kind, name)
                    )
                    ids.append(cur.lastrowid)
        db.commit()
        return ids
    except Exception:
        db.rollback()
        raise
