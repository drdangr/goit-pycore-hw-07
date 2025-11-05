from __future__ import annotations # для підтримки типів, які визначені пізніше в коді

from collections import UserDict
from typing import List, Optional
from datetime import datetime, date, timedelta


# БАЗОВІ ТИПИ ПОЛІВ 

class Field:
    """
    Базовий клас для полів запису 
    """
    def __init__(self, value: str):
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


#  Поле Birthday 
class Birthday(Field):
    """
    Поле дня народження з валідацією формату DD.MM.YYYY та збереженням як date.
    """
    def __init__(self, value: str):
        # одразу парсимо та перевіряємо
        dt = self._parse(value)
        super().__init__(dt)  # value тут буде об'єктом date

    @staticmethod
    def _parse(s: str) -> date:
        s = s.strip()
        try:
            # формат строго DD.MM.YYYY
            return datetime.strptime(s, "%d.%m.%Y").date()
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")

    @property
    def value(self) -> date:
        return self._value

    @value.setter
    def value(self, v: str | date) -> None:
        # дозволяємо встановлювати або рядок (який парсимо), або вже date
        if isinstance(v, date):
            self._value = v
        else:
            self._value = self._parse(v)

    def __str__(self) -> str:
        # зворотне перетворення у формат DD.MM.YYYY для виводу
        return self.value.strftime("%d.%m.%Y")

# ЗАПИС КОНТАКТУ 

class Record:
    """
    Один запис адресної книги: ім'я + список телефонів.
    - name: об'єкт Name
    - phones: список об'єктів Phone
    """
    def __init__(self, name: str):
        self.name = Name(name)
        self.phones: List[Phone] = []
        self.birthday: Birthday | None = None  # додаткове поле дня народження

    #  операції з телефонами 

    def add_phone(self, phone: str | Phone) -> None:
        """
        Додає телефон. Приймає або сирий рядок (10 цифр), або готовий Phone.
        Дублікати не забороняємо за умовчанням.
        """
        p = phone if isinstance(phone, Phone) else Phone(phone)
        self.phones.append(p)

    def remove_phone(self, phone_value: str) -> bool:
        """
        Видаляє ПЕРШИЙ знайдений телефон за значенням (рядок з 10 цифр).
        Повертає True, якщо видалили; False — якщо не знайдено.
        """
        target = self.find_phone(phone_value)
        if target:
            self.phones.remove(target)
            return True
        return False

    def edit_phone(self, old_value: str, new_value: str) -> bool:
        """
        Знаходить перший телефон зі значенням old_value і заміняє його на new_value.
        Повертає True, якщо успішно; False — якщо старий не знайдено.
        """
        target = self.find_phone(old_value)
        if not target:
            return False
        target.value = new_value  # валідація відбудеться у Phone.value.setter
        return True

    def find_phone(self, phone_value: str) -> Optional[Phone]:
        """
        Повертає об'єкт Phone за значенням (10 цифр) або None, якщо не знайдено.
        Нормалізуємо.
        """
        try:
            normalized = Phone._normalize_and_validate(phone_value)
        except ValueError:
            # якщо вхід не 10 цифр — одразу None (шукати нема сенсу)
            return None

        for p in self.phones:
            if p.value == normalized:
                return p
        return None

    def __str__(self) -> str:
        parts = [f"Contact name: {self.name.value}"]
        if self.phones:
            parts.append(f"phones: {'; '.join(p.value for p in self.phones)}")
        if self.birthday:
            parts.append(f"birthday: {self.birthday}")
        return ", ".join(parts)
    
    #  операції з днем народження
    def add_birthday(self, date_str: str) -> None:
        """
        Додає або оновлює день народження у форматі DD.MM.YYYY.
        """
        # Якщо хочеш заборонити перезапис — заміни на:
        # if self.birthday is not None: raise ValueError("Birthday already set")
        self.birthday = Birthday(date_str)

    def get_birthday_str(self) -> str | None:
        """
        Повертає дату народження у форматі DD.MM.YYYY або None.
        """
        return str(self.birthday) if self.birthday else None


# АДРЕСНА КНИГА 

class AddressBook(UserDict):
    """
    Колекція записів (Record), ключ — ІМ'Я (рядок). Спадкуємося від UserDict
    зберігаємо у self.data словник {name_str: Record}.
    """

    def add_record(self, record: Record) -> None:
        """
        Додає запис у книгу. Ключ — точне ім'я (як у record.name.value).
        Якщо ім'я вже існує, перезаписує .
        """
        self.data[record.name.value] = record

    def find(self, name: str) -> Optional[Record]:
        """
        Пошук запису за ІМ'ЯМ (точний збіг, регістр важливий ).
        Повертає Record або None, якщо не знайдено.
        """
        return self.data.get(name)

    def delete(self, name: str) -> bool:
        """
        Видалення запису за ІМ'ЯМ. Повертає True — якщо видалили, False — якщо ні.
        """
        if name in self.data:
            del self.data[name]
            return True
        return False
    
    def get_birthday_by_name(self, name: str) -> str | None:
        """
        Повертає дату народження контакту за іменем або None, якщо не знайдено.
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

        # мапа день_тижня -> список імен
        buckets: dict[int, list[str]] = {}

        for rec in self.data.values():
            if rec.birthday is None:
                continue
            bday = rec.birthday.value  # date (рік народження неважливий)
            # обчислюємо наступний день народження у поточному році
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
            

# ДЕМО-СЦЕНАРІЙ З ТЗ 
if __name__ == "__main__":
   # Створення нової адресної книги
    book = AddressBook()

    # Створення запису для John
    john_record = Record("John")
    john_record.add_phone("1234567890")
    john_record.add_phone("5555555555")

    # Додавання запису John до адресної книги
    book.add_record(john_record)

    # Створення та додавання нового запису для Jane
    jane_record = Record("Jane")
    jane_record.add_phone("9876543210")
    book.add_record(jane_record)

    # Виведення всіх записів у книзі
    for name, record in book.data.items():
        print(record)

    # Знаходження та редагування телефону для John
    john = book.find("John")
    john.edit_phone("1234567890", "1112223333")

    print(john)  # Виведення: Contact name: John, phones: 1112223333; 5555555555

    # Пошук конкретного телефону у записі John
    found_phone = john.find_phone("5555555555")
    print(found_phone)  # Виведення: 5555555555
    #print(f"{john.name}: {found_phone}") # Виведення: Name object + Phone object не в ТЗ, але для перевірки

    # Видалення запису Jane
    book.delete("Jane")

    # Виведення всіх записів після видалення Jane - нема в ТЗ, але для перевірки
    print("\nAfter deleting Jane:")
    for name, record in book.data.items():
        print(record)

    # Додавання днів народження
    john.add_birthday("15.09.1990") # John  

    # --- Повернемо Jane ------------------------------------------
    jane_record = Record("Jane")
    jane_record.add_phone("9876543210")
    book.add_record(jane_record)
    jane = book.find("Jane")
    
    # Додамо день ії народження 
    jane.add_birthday("17.09.1992") # Jane
    #-------------------------------------------------------------

    # Виведення всіх записів після додавання Jane назад - нема в ТЗ, але для перевірки
    print("\nAfter adding Jane back, and adding they Birthdays:")
    for name, record in book.data.items():
        print(record)
    


    # Припустимо, сьогодні 10 вересня 2023 року
    test_date = date(2023, 9, 10)
    upcoming = book.get_upcoming_birthdays(base_date=test_date)
    print("\nUpcoming Birthdays:")  
    for line in upcoming:
        print(line)
        