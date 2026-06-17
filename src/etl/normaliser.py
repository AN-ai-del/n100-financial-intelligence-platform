def normalize_year(value):
    """
    Convert year values like 2024, '2024', 'FY 2024', 'Mar 2024'
    into integer year.
    """
    if value is None:
        return None

    text = str(value).strip()

    for part in text.replace("-", " ").replace("_", " ").split():
        if part.isdigit() and len(part) == 4:
            return int(part)

    if text.isdigit():
        return int(text)

    return None


def normalize_ticker(value):
    """
    Clean ticker/company symbols.
    Example: ' tcs ' -> 'TCS'
    """
    if value is None:
        return None

    return str(value).strip().upper()