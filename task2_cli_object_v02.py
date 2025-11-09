from __future__ import annotations  # підтримка посилань на типи, оголошені нижче

from collections import UserDict
from typing import List, Optional, Callable, Tuple
from datetime import datetime, date, timedelta
import functools


# =========================
# Декоратор єдиного оброблення помилок
# =========================
def input_error(func: Callable[..., str]) -> Callable[..., str]:
    """
    Обгортає хендлер команди та перехоплює типові помилки введення користувача,
    повертаючи дружні повідомлення замість падіння програми.
    """
    @functools.wraps(func)
    def inner(*args, **kwargs) -> str:
        try:
            return func(*args, **kwargs)
        except KeyError as e:
            # ім'я передаємо в KeyError(name), щоб зробити дружнє повідомлення
            name = (e.args[0] if e.args else "").strip() or "<?>"
            return f"Contact '{name}' not found."
        except IndexError:
            return "Not enough arguments for this command."
        except ValueError as e:
            msg = (str(e).strip() or "Invalid value.")
            return msg
    return inner


# =====================
# Парсер вводу
# =====================
def parse_input(user_input: str) -> Tuple[str, List[str]]:
    """
    Розбирає введення користувача на команду та аргументи.
    Повертає: (command_lower, args_list)
    """
    parts = user_input.strip().split()
    if not parts:
        return "", []
    return parts[0].lower(), parts[1:]


# =====================
# БАЗОВІ ТИПИ ПОЛІВ
# =====================
class Field:
    """Базовий клас для полів запису."""
    def __init__(self, value):
        self.value = value

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value!r})"


class Name(Field):
    """Обов'язкове поле — ім'я контакту."""
    def __init__(self, value: str):
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name cannot be empty.")
        super().__init__(cleaned)


class Phone(Field):
    """
    Телефон з валідацією: РІВНО 10 цифр (без «очищення» сторонніх символів).
    """
    def __init__(self, value: str):
        super().__init__(self._validate(value))

    @staticmethod
    def _validate(raw: str) -> str:
        s = raw.strip()
        if len(s) != 10 or not s.isdigit():
            raise ValueError("Phone must contain exactly 10 digits.")
        return s

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, v: str) -> None:
        self._value = self._validate(v)


class Birthday(Field):
    """
    День народження з валідацією формату DD.MM.YYYY та збереженням як date.
    """
    def __init__(self, value: str | date):
        dt = value if isinstance(value, date) else self._parse(value)
        super().__init__(dt)

    @staticmethod
    def _parse(s: str) -> date:
        s = s.strip()
        try:
            return datetime.strptime(s, "%d.%m.%Y").date()
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")

    @property
    def value(self) -> date:
        return self._value

    @value.setter
    def value(self, v: str | date) -> None:
        if isinstance(v, date):
            self._value = v
        else:
            self._value = self._parse(v)

    def __str__(self) -> str:
        return self.value.strftime("%d.%m.%Y")


# =================
# ЗАПИС КОНТАКТУ
# =================
class Record:
    """
    Один запис адресної книги: ім'я + телефони + (необов'язковий) день народження.
    - name: Name
    - phones: List[Phone]
    - birthday: Birthday | None
    """
    def __init__(self, name: str):
        self.name = Name(name)
        self.phones: List[Phone] = []
        self.birthday: Birthday | None = None

    # ---- телефони ----
    def add_phone(self, phone: str) -> None:
        self.phones.append(Phone(phone))  # валідація в Phone

    def remove_phone(self, phone_value: str) -> bool:
        target = self.find_phone(phone_value)  # тут може піднятися ValueError, і це ок
        if target:
            self.phones.remove(target)
            return True
        return False

    def edit_phone(self, old_value: str, new_value: str) -> bool:
        target = self.find_phone(old_value)  # якщо формат old_value поганий — ValueError
        if not target:
            return False
        target.value = new_value  # валідація нового значення тут же
        return True

    def find_phone(self, phone_value: str) -> Optional[Phone]:
        normalized = Phone._validate(phone_value)
        for p in self.phones:
            if p.value == normalized:
                return p
        return None

    # ---- день народження ----
    def add_birthday(self, date_str: str) -> None:
        """Додає або оновлює день народження у форматі DD.MM.YYYY."""
        self.birthday = Birthday(date_str)

    def get_birthday_str(self) -> Optional[str]:
        """Повертає дату народження у форматі DD.MM.YYYY або None."""
        return str(self.birthday) if self.birthday else None

    def __str__(self) -> str:
        # Акуратний «людський» вивід: показує лише наявні поля
        parts = [f"Contact name: {self.name.value}"]
        if self.phones:
            parts.append(f"phones: {'; '.join(p.value for p in self.phones)}")
        if self.birthday:
            parts.append(f"birthday: {self.birthday}")
        return ", ".join(parts)


# ==========================
# Книга контактів (словник)
# ==========================
class AddressBook(UserDict):
    """
    Колекція записів (Record), ключ — ім'я (рядок). Зберігаємо у self.data: {name: Record}.
    """
    def add_record(self, record: Record) -> None:
        self.data[record.name.value] = record

    def find(self, name: str) -> Optional[Record]:
        return self.data.get(name)

    def delete(self, name: str) -> bool:
        if name in self.data:
            del self.data[name]
            return True
        return False

    def get_birthday_by_name(self, name: str) -> Optional[str]:
        rec = self.find(name)
        if rec and rec.birthday:
            return rec.get_birthday_str()
        return None

    def get_upcoming_birthdays(self, base_date: date | None = None) -> list[str]:
        """
        Повертає список рядків з деталями:
        'Monday: John — 15.09.1990 (Tuesday), Jane — 17.09.1992 (Sunday)'
        Групування за днем ПРИВІТАННЯ (вихідні переносяться на понеділок),
        у дужках — фактичний день тижня для дня народження в поточному/наступному році.
        """
        today = base_date or date.today()
        start = today #+ timedelta(days=1) після тестування я вирішив залишити сьогоднішній день включеним
        end = today + timedelta(days=7)
        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        # wd -> list[str] (елементи формату "Name — DD.MM.YYYY (Weekday)")
        buckets: dict[int, list[str]] = {}

        for rec in self.data.values():
            if rec.birthday is None:
                continue

            orig_bday: date = rec.birthday.value
            next_bday = orig_bday.replace(year=today.year)
            if next_bday < start:
                next_bday = orig_bday.replace(year=today.year + 1)

            # тільки якщо у вікні [start; end]
            if start <= next_bday <= end:
                orig_wd = next_bday.weekday()  # 0=Mon..6=Sun
                congratulate_wd = 0 if orig_wd in (5, 6) else orig_wd

                detail = f"{rec.name.value} — {orig_bday.strftime('%d.%m.%Y')} ({weekday_names[orig_wd]})"
                buckets.setdefault(congratulate_wd, []).append(detail)
        # Формуємо вихідний список рядків
        result: list[str] = []
        for wd in range(7):
            if wd in buckets:
                # відсортуємо вallсередині дня по імені для стабільності
                day_items = sorted(buckets[wd], key=lambda s: s.split(' — ', 1)[0].lower())
                result.append(f"{weekday_names[wd]}:\n" + "\n".join(day_items))
        return result


# =========================
# CLI: довідка та хендлери
# =========================
def help_command() -> str:
    return (
        "Available commands:\n"
        "- hello — greeting\n"
        "- add <name> [phone] — add a new contact (optionally with phone) / add phone to existing\n"
        "- change <name> <old_phone> <new_phone> — change phone\n"
        "- phone <name> — show phone numbers\n"
        "- all — show all contacts\n"
        "- add-birthday <name> <DD.MM.YYYY> — add/update birthday\n"
        "- show-birthday <name> — show contact birthday\n"
        "- birthdays — show upcoming birthdays for next 7 days\n"
        "- help — show this message\n"
        "- exit / close — quit"
    )


@input_error
def add_contact(args: List[str], book: AddressBook) -> str:
    """
    add <name> [phone]
    Додає новий контакт (з телефоном або без) або додає телефон до існуючого.
    """
    if not args:
        return "Please provide a name."
    name = args[0]
    phone = args[1] if len(args) > 1 else None

    record = book.find(name)
    message = "Contact updated."
    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."
    if phone:
        record.add_phone(phone)
    return message


@input_error
def change_phone(args: List[str], book: AddressBook) -> str:
    """
    change <name> <old_phone> <new_phone>
    Змінює перше входження старого номера на новий (усі три аргументи обов'язкові).
    """
    if len(args) < 3:
        return "Usage: change <name> <old_phone> <new_phone>"
    name, old_phone, new_phone = args[0], args[1], args[2]
    record = book.find(name)
    if record is None:
        raise KeyError(name)
    ok = record.edit_phone(old_phone, new_phone)
    return "Phone changed." if ok else "Old phone not found."


@input_error
def show_phones(args: List[str], book: AddressBook) -> str:
    """
    phone <name>
    Показує телефони контакту.
    """
    if not args:
        return "Usage: phone <name>"
    name = args[0]
    record = book.find(name)
    if record is None:
        raise KeyError(name)
    if not record.phones:
        return "No phones."
    nums = "; ".join(p.value for p in record.phones)
    return f"{name}: {nums}"


@input_error
def show_all(book: AddressBook) -> str:
    """
    all
    Повертає всі записи адресної книги у зручному вигляді.
    """
    if not book.data:
        return "No contacts."
    return "\n".join(str(rec) for rec in book.data.values())


@input_error
def add_birthday(args: List[str], book: AddressBook) -> str:
    """
    add-birthday <name> <DD.MM.YYYY>
    Додає або оновлює день народження контакту.
    """
    if len(args) < 2:
        return "Usage: add-birthday <name> <DD.MM.YYYY>"
    name, bday_str = args[0], args[1]
    record = book.find(name)
    if record is None:
        record = Record(name)
        book.add_record(record)
    record.add_birthday(bday_str)  # валідація у Birthday
    return "Birthday added."


@input_error
def show_birthday(args: List[str], book: AddressBook) -> str:
    """
    show-birthday <name>
    Показує день народження контакту.
    """
    if not args:
        return "Usage: show-birthday <name>"
    name = args[0]
    record = book.find(name)
    if record is None:
        raise KeyError(name)
    b = record.get_birthday_str()
    return f"{name}: {b}" if b else "No birthday set."


@input_error
def birthdays(args: List[str], book: AddressBook) -> str:
    """
    birthdays
    Повертає список користувачів, яких потрібно привітати протягом наступного тижня.
    """
    lines = book.get_upcoming_birthdays()
    if not lines:
        return "No birthdays next week."
    return "\n".join(lines)


# =================
# ГОЛОВНИЙ ЦИКЛ
# =================
def main():
    book = AddressBook()
    print("Welcome to the assistant bot!")
    while True:
        command, args = parse_input(input("Enter a command: "))

        if command in ("close", "exit"):
            print("Good bye!")
            break

        elif command == "hello":
            print("How can I help you?")

        elif command == "add":
            print(add_contact(args, book))

        elif command == "change":
            print(change_phone(args, book))

        elif command == "phone":
            print(show_phones(args, book))

        elif command == "all":
            print(show_all(book))

        elif command == "add-birthday":
            print(add_birthday(args, book))

        elif command == "show-birthday":
            print(show_birthday(args, book))

        elif command == "birthdays":
            print(birthdays(args, book))

        elif command == "help":
            print(help_command())

        elif command == "":
            print("Enter a command or type 'help'.")

        else:
            print(f"Unknown command: '{command}'")
            print(help_command())


if __name__ == "__main__":
    main()
