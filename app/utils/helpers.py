from datetime import datetime


def format_date(date_int: int) -> str:
    date_str = str(date_int)
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return str(date_int)


def parse_date(date_str: str) -> int:
    date_str = date_str.replace('-', '')
    return int(date_str)


def format_number(num: float, decimals: int = 2) -> str:
    return f"{num:.{decimals}f}"


def format_percent(num: float) -> str:
    return f"{num:.2f}%"
