from __future__ import annotations  # для підтримки типів, які визначені пізніше в коді

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

        # Коли контакт не знайдено (ім'я передається в KeyError)
        except KeyError as e:
            name = (e.args[0] if e.args else "").strip() or "<?>"
            return f"Contact '{name}' not found."

        # Коли бракує або неправильні аргументи
        except IndexError:
            return "Enter the argument for the command"

        # Некоректні значення (наприклад, телефон не з 10 цифр, або дата не DD.MM.YYYY)
        except ValueError as e:
            msg = (str(e).strip() or "Invalid arguments.")
            return msg

    return inner


# =====================
# Розбір рядка вводу
# =====================
def parse_input(user_input: str) -> Tuple[str, ...]:
    """
    Повертає кортеж: (команда, *аргументи).
    Порожній ввід → ("", []).
    """
    parts = user_input.strip().split()
    if not parts:
        return "", []
    cmd, *args = parts
    return cmd.lower(), *args


# =====================
# БАЗОВІ ТИПИ ПОЛІВ
# =====================
class Field:
    """
    Базовий клас для полів запису
    """
    def __init__(self, value):
        self.value = value  # у нащадків буде валідація через property

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value!r})"


class Name(Field):
    """
    Обов'язкове поле — ім'я контакту.
    """
    def __init__(self, value: str):
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name cannot be empty.")
        super().__init__(cleaned)


class Phone(Field):
    """
    Телефон з валідацією: рівно 10 цифр.
    """
    def __init__(self, value: str):
        super().__init__(self._normalize_and_validate(value))

    @staticmethod
    def _normalize_and_validate(raw: str) -> str:
        s = "".join(ch for ch in raw if ch.isdigit())  # залишаємо тільки цифри
        if len(s) != 10:
            raise ValueError("Phone must contain exactly 10 digits.")
        return s

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, v: str) -> None:
        # setter викликається і з __init__, і при подальших змінах
        self._value = self._normalize_and_validate(v)


class Birthday(Field):
    """
    Поле дня народження з валідацією формату DD.MM.YYYY та збереженням як date.
    """
    def __init__(self, value: str | date):
        dt = value if isinstance(value, date) else self._parse(value)
        super().__init__(dt)  # value тут буде об'єктом date

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
        # зворотне перетворення у формат DD.MM.YYYY для виводу
        return self.value.strftime("%d.%m.%Y")


# =================
# ЗАПИС КОНТАКТУ
# =================
class Record:
    """
    Один запис адресної книги: ім'я + телефони + (необов'язковий) день народження.
    - name: об'єкт Name
    - phones: список об'єктів Phone
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
        Дублікати не забороняємо за умовчанням (ТЗ не вимагає).
        """
        p = phone if isinstance(phone, Phone) else Phone(phone)
        self.phones.append(p)

    def remove_phone(self, phone_value: str) -> bool:
        """
        Видаляє ПЕРШИЙ знайдений телефон за значенням. True/False.
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
       """
       Повертає зручний для читання рядок з інформацією про контакт.
       """
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
    Колекція записів (Record), ключ — ІМ'Я (рядок). Спадкуємося від UserDict,
    зберігаємо у self.data словник {name_str: Record}.
    """

    def add_record(self, record: Record) -> None:
        """
        Додає запис у книгу. Ключ — точне ім'я (як у record.name.value).
        Якщо ім'я вже існує — перезаписує.
        """
        self.data[record.name.value] = record

    def find(self, name: str) -> Optional[Record]:
        """
        Пошук запису за ІМ'ЯМ (точний збіг, регістр важливий).
        """
        return self.data.get(name)

    def delete(self, name: str) -> bool:
        """
        Видалення запису за ІМ'ЯМ. True — якщо видалили; False — якщо ні.
        """
        if name in self.data:
            del self.data[name]
            return True
        return False

    def get_birthday_by_name(self, name: str) -> Optional[str]:
        """
        Повертає дату народження контакту за іменем або None, якщо не знайдено/не задано.
        """
        record = self.find(name)
        if record and record.birthday:
            return record.get_birthday_str()
        return None

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

        # інтервал у 7 днів, не включаючи сьогодні: (today+1 .. today+7)
        start = today + timedelta(days=1)
        end = today + timedelta(days=7)

        buckets: dict[int, list[str]] = {}

        for rec in self.data.values():
            if rec.birthday is None:
                continue
            bday = rec.birthday.value  # date (рік народження неважливий)
            next_bday = bday.replace(year=today.year)
            if next_bday < start:
                # якщо вже минув у цьому вікні — дивимось наступний рік
                next_bday = bday.replace(year=today.year + 1)

            if start <= next_bday <= end:
                weekday = next_bday.weekday()  # 0=Mon ... 6=Sun
                # перенос вихідних на понеділок
                if weekday in (5, 6):  # Saturday або Sunday
                    weekday = 0  # Monday
                buckets.setdefault(weekday, []).append(rec.name.value)

        # Формуємо вихідний список рядків
        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        result: list[str] = []
        for wd in range(7):
            if wd in buckets:
                names = ", ".join(sorted(buckets[wd]))
                result.append(f"{weekday_names[wd]}: {names}")
        return result


# =========================
# CLI: довідка та хендлери
# =========================
def help_command() -> str:
    """
    Довідка по доступним командам бота.
    """
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
def add_contact(args: list[str], book: AddressBook) -> str:
    """
    add <name> [phone]
    Додає новий контакт (без телефону або з телефоном) або додає телефон до існуючого.
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
        record.add_phone(phone)  # валідація усередині Phone

    return message


@input_error
def change_phone(args: list[str], book: AddressBook) -> str:
    """
    change <name> <old_phone> <new_phone>
    Змінює перше входження старого номера на новий.
    """
    name, old_phone, new_phone, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError(name)
    ok = record.edit_phone(old_phone, new_phone)
    return "Phone changed." if ok else "Old phone not found."


@input_error
def show_phones(args: list[str], book: AddressBook) -> str:
    """
    phone <name>
    Показує телефони контакту.
    """
    name, *_ = args
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
    Повертає всі записи адресної книги у зручному для читання вигляді.
    """
    if not book.data:
        return "No contacts."
    lines = [str(rec) for rec in book.data.values()]
    return "\n".join(lines)


@input_error
def add_birthday(args: list[str], book: AddressBook) -> str:
    """
    add-birthday <name> <DD.MM.YYYY>
    Додає або оновлює день народження контакту.
    """
    name, bday_str, *_ = args
    record = book.find(name)
    if record is None:
        # Зручно: створюємо контакт автоматично, якщо його ще немає
        record = Record(name)
        book.add_record(record)
    record.add_birthday(bday_str)  # валідація всередині Birthday
    return "Birthday added."


@input_error
def show_birthday(args: list[str], book: AddressBook) -> str:
    """
    show-birthday <name>
    Показує день народження контакту.
    """
    name, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError(name)
    b = record.get_birthday_str()
    return f"{name}: {b}" if b else "No birthday set."


@input_error
def birthdays(args: list[str], book: AddressBook) -> str:
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
        command, *args = parse_input(input("Enter a command: "))

        if command in ("close", "exit"):
            print("Good bye!")
            break

        if command == "hello":
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
            # Порожній ввід: підказка користувачу
            print("Enter a command or type 'help'.")

        else:
            # Невідома команда
            print(f"Unknown command: '{command}'")
            print(help_command())


if __name__ == "__main__":
    main()
