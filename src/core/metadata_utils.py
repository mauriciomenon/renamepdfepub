from typing import List

def normalize_authors(values) -> List[str]:
    """Normalize various author representations into a flat list of strings.

    - Accepts strings, numbers, dicts with name/given/family, and nested lists.
    - Strips whitespace, removes empties, and de-duplicates preserving order.
    """
    result: List[str] = []
    if values is None:
        return result
    if isinstance(values, (str, int, float)):
        s = str(values).strip()
        return [s] if s else []
    try:
        for v in values:
            if v is None:
                continue
            if isinstance(v, (str, int, float)):
                s = str(v).strip()
                if s:
                    result.append(s)
            elif isinstance(v, dict):
                name = v.get('name') or v.get('full_name') or ''
                if not name:
                    g = v.get('given') or v.get('first') or ''
                    f = v.get('family') or v.get('last') or ''
                    name = f"{g} {f}".strip()
                if name:
                    result.append(str(name))
            elif isinstance(v, (list, tuple, set)):
                result.extend(normalize_authors(list(v)))
            else:
                s = str(v).strip()
                if s:
                    result.append(s)
    except Exception:
        return [str(values)] if values else []

    seen = set()
    out: List[str] = []
    for s in result:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out

