from __future__ import annotations

from collections import UserDict
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple, Callable
import functools


# =========================
# Декоратор обробки помилок
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

        # Коли контакт не знайдено (ім'я передається в KeyError)
        except KeyError as e:
            name = (e.args[0] if e.args else "").strip() or "<?>"
            return f"Contact '{name}' not found."

        # Некоректний формат даних користувачем
        except ValueError as e:
            # Якщо ValueError без повідомлення — даємо узагальнене
            msg = str(e).strip() or "Invalid value."
            return msg

        # Недостатньо аргументів команди
        except IndexError:
            return "Not enough arguments for this command."

    return inner


# =====================
# Базові класи моделей
# =====================
class Field:
    """Базовий клас для полів запису (узагальнений контейнер для value)."""

    def __init__(self, value):
        self.value = value  # у нащадків може бути валідація через property

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
    Телефон з валідацією: РІВНО 10 цифр.
    Дозволяємо на вхід «сирий» рядок — нормалізуємо в сеттері.
    """

    def __init__(self, value: str):
        super().__init__(self._normalize_and_validate(value))

    @staticmethod
    def _normalize_and_validate(raw: str) -> str:
        s = "".join(ch for ch in raw if ch.isdigit())
        if len(s) != 10:
            raise ValueError("Phone must contain exactly 10 digits.")
        return s

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, v: str) -> None:
        self._value = self._normalize_and_validate(v)


class Birthday(Field):
    """
    Поле дня народження з валідацією формату DD.MM.YYYY та збереженням як date.
    """

    def __init__(self, value: str | date):
        if isinstance(value, date):
            parsed = value
        else:
            parsed = self._parse(value)
        super().__init__(parsed)

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
# Клас одного запису
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
    def add_phone(self, phone: str | Phone) -> None:
        """
        Додає телефон. Приймає або сирий рядок (10 цифр), або готовий Phone.
        Дублікатів ТЗ не забороняє — при потребі можна додати перевірку.
        """
        p = phone if isinstance(phone, Phone) else Phone(phone)
        self.phones.append(p)

    def remove_phone(self, phone_value: str) -> bool:
        """
        Видаляє ПЕРШИЙ знайдений телефон за значенням (рядок з 10 цифр). True/False.
        """
        target = self.find_phone(phone_value)
        if target:
            self.phones.remove(target)
            return True
        return False

    def edit_phone(self, old_value: str, new_value: str) -> bool:
        """
        Замінює ПЕРШЕ входження old_value на new_value. True/False.
        Валідація нового значення відбувається у Phone.value.setter.
        """
        target = self.find_phone(old_value)
        if not target:
            return False
        target.value = new_value
        return True

    def find_phone(self, phone_value: str) -> Optional[Phone]:
        """
        Повертає об'єкт Phone за значенням (10 цифр) або None.
        Приймає «сирий» рядок — нормалізуємо перед пошуком.
        """
        try:
            normalized = Phone._normalize_and_validate(phone_value)
        except ValueError:
            return None

        for p in self.phones:
            if p.value == normalized:
                return p
        return None

    # ---- день народження ----
    def add_birthday(self, date_str: str) -> None:
        """
        Додає або оновлює день народження у форматі DD.MM.YYYY.
        """
        self.birthday = Birthday(date_str)

    def get_birthday_str(self) -> Optional[str]:
        """
        Повертає дату народження у форматі DD.MM.YYYY або None.
        """
        return str(self.birthday) if self.birthday else None

    def __str__(self) -> str:
        phones_str = "; ".join(p.value for p in self.phones) if self.phones else "-"
        bday_str = self.get_birthday_str() or "-"
        return f"Contact name: {self.name.value}, phones: {phones_str}, birthday: {bday_str}"


# ==========================
# Книга контактів (словник)
# ==========================
class AddressBook(UserDict):
    """
    Колекція записів (Record), ключ — ІМ'Я (рядок). Спадкуємося від UserDict
    для зручності, зберігаємо у self.data словник {name_str: Record}.
    """

    def add_record(self, record: Record) -> None:
        """
        Додає запис у книгу. Ключ — точне ім'я (як у record.name.value).
        Якщо ім'я вже існує — перезаписує (поведінку можна змінити за потреби).
        """
        self.data[record.name.value] = record

    def find(self, name: str) -> Optional[Record]:
        """
        Пошук запису за ІМ'ЯМ (точний збіг, регістр важливий).
        """
        return self.data.get(name)

    def delete(self, name: str) -> bool:
        """
        Видалення запису за ІМ'ЯМ. True — якщо видалили; False — якщо не знайдено.
        """
        if name in self.data:
            del self.data[name]
            return True
        return False

    def get_upcoming_birthdays(self, base_date: date | None = None) -> list[str]:
        """
        Повертає список рядків виду:
        'Monday: John, Jane'
        для користувачів, яких потрібно привітати протягом наступного тижня.
        Вихідні (сб/нд) переносяться на понеділок.
        """
        if base_date is None:
            today = date.today()
        else:
            today = base_date

        # Інтервал 7 днів уперед (без сьогодні): (today+1 .. today+7)
        start = today + timedelta(days=1)
        end = today + timedelta(days=7)

        buckets: dict[int, list[str]] = {}

        for rec in self.data.values():
            if rec.birthday is None:
                continue
            bday = rec.birthday.value  # type: ignore[attr-defined]
            # День народження в поточному році
            next_bday = bday.replace(year=today.year)
            # Якщо поточний рік вже пройшов для інтервалу — дивимось наступний
            if next_bday < start:
                next_bday = bday.replace(year=today.year + 1)

            if start <= next_bday <= end:
                weekday = next_bday.weekday()  # 0=Mon ... 6=Sun
                # Перенос вікандів на понеділок
                if weekday in (5, 6):
                    weekday = 0
                buckets.setdefault(weekday, []).append(rec.name.value)

        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        result: list[str] = []
        for wd in range(7):
            if wd in buckets:
                names = ", ".join(sorted(buckets[wd]))
                result.append(f"{weekday_names[wd]}: {names}")
        return result


# =========================
# CLI: парсер і хендлери
# =========================
def parse_input(user_input: str) -> Tuple[str, List[str]]:
    """
    Розбирає введення користувача на команду та аргументи.
    Повертає: (command_lower, args_list)
    """
    parts = user_input.strip().split()
    if not parts:
        return "", []
    return parts[0].lower(), parts[1:]


@input_error
def add_contact(args, book: AddressBook) -> str:
    """
    add [ім'я] [телефон]
    Додає новий контакт або телефон до існуючого.
    """
    name, phone, *_ = args
    record = book.find(name)
    message = "Contact updated."
    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."
    if phone:
        record.add_phone(phone)  # валідація усередині Phone
    return message


@input_error
def change_phone(args, book: AddressBook) -> str:
    """
    change [ім'я] [старий телефон] [новий телефон]
    Змінює перше входження старого номера на новий.
    """
    name, old_phone, new_phone, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError(name)
    ok = record.edit_phone(old_phone, new_phone)
    return "Phone changed." if ok else "Old phone not found."


@input_error
def show_phones(args, book: AddressBook) -> str:
    """
    phone [ім'я]
    Показує телефони контакту.
    """
    name, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError(name)
    if not record.phones:
        return "No phones."
    nums = ", ".join(p.value for p in record.phones)
    return f"{name}: {nums}"


@input_error
def show_all(book: AddressBook) -> str:
    """
    all
    Повертає всі записи адресної книги у зручному для читання вигляді.
    """
    if not book.data:
        return "No contacts."
    lines = [str(rec) for rec in book.data.values()]
    return "\n".join(lines)


@input_error
def add_birthday(args, book: AddressBook) -> str:
    """
    add-birthday [ім'я] [DD.MM.YYYY]
    Додає / оновлює день народження контакту.
    """
    name, bday_str, *_ = args
    record = book.find(name)
    if record is None:
        # Якщо контакту немає — створюємо його (зручно для користувача)
        record = Record(name)
        book.add_record(record)
    record.add_birthday(bday_str)  # валідація усередині Birthday
    return "Birthday added."


@input_error
def show_birthday(args, book: AddressBook) -> str:
    """
    show-birthday [ім'я]
    Показує день народження контакту.
    """
    name, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError(name)
    b = record.get_birthday_str()
    return f"{name}: {b}" if b else "No birthday set."


@input_error
def birthdays(args, book: AddressBook) -> str:
    """
    birthdays
    Повертає список користувачів, яких потрібно привітати протягом наступного тижня.
    """
    lines = book.get_upcoming_birthdays()
    if not lines:
        return "No birthdays next week."
    return "\n".join(lines)


# =========
# ГОЛОВНИЙ ЦИКЛ
# =========
def main():
    book = AddressBook()
    print("Welcome to the assistant bot!")
    while True:
        user_input = input("Enter a command: ")
        command, args = parse_input(user_input)

        if command in ["close", "exit"]:
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

        else:
            print("Invalid command.")


if __name__ == "__main__":
    main()
