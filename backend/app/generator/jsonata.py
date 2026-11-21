"""Warunki widoczności (JSONata) w składni używanej przez referencyjne eksporty."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldRef:
    """Adres pola: strona → sekcja → pole."""

    tab: str
    section: str
    field: str

    def answer(self) -> str:
        return (f"tabs['{self.tab}' in title].questions['{self.section}' in field.techName]"
                f".field.repeatingSectionGrid['{self.field}' in field.techName].field.__userAnswer")


def equals(ref: FieldRef, value: str) -> str:
    value = value.replace('"', '\\"')
    return f'("{value}" in {ref.answer()})'


def not_equals(ref: FieldRef, value: str) -> str:
    return f"$not{equals(ref, value)}"


def all_of(*queries: str) -> str:
    return "\r\nand\r\n".join(queries)


def any_of(*queries: str) -> str:
    return "(\r\n" + "\r\nor\r\n".join(queries) + "\r\n)"


def show(query: str) -> list[dict[str, str]]:
    return [{"type": "SHOW", "query": query}]
