from datetime import date
from typing import Literal
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    FileExtensionValidator,
    RegexValidator,
)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import Q
from . import util
import math
from datetime import date
import datetime
import time

##########
#
# Списки для вида страхования 
# и статуса договора
#
##########
ContractTypes = {
    "house": "Страхование недвижимости",
    "personinsurance": "Страхование жизни"
}

ContractStatuses = {
    'active': 'Активный',
    'terminated': 'Расторжен',
    'insurance_incident': 'Наступил страховой случай'
}


##########
#
# Модели
#
##########

class Pasport(models.Model):
    series = models.SmallIntegerField(
        "Серия",
        validators=[RegexValidator(r"\d{4}", "Серия указана неверно")],
    )

    number = models.IntegerField(
        "Номер",
        validators=[RegexValidator(r"\d{6}", "Номер указан неверно")],
    )

    date_of_issue = util.ModelDateField(
        "Дата выдачи",
        validators=[
            MaxValueValidator(
                date.today, "Дата выдачи не может быть больше текущего дня"
            )
        ],
    )

    who_issued = models.CharField("Кем выдан", max_length=200)

    who_issued_code = models.IntegerField(
        "Код подразделения",
        validators=[
            RegexValidator(r"\d{6}", "Код подразделения должен быть 6-значным")
        ],
    )

    scan = models.FileField(
        upload_to="pasport/%Y/%m/%d/",
        verbose_name="Скан паспорта",
        validators=[
            FileExtensionValidator(
                ["pdf", "PDF"], "Поддерждиваются только PDF файлы", 400
            )
        ],
    )

    class Meta:
        db_table = 'pasport'
        verbose_name = "Паспорт"
        verbose_name_plural = "Паспорта"

    def __str__(self) -> str:
        return "{0}-{1} {2}".format(self.series, self.number, self.date_of_issue)


class Person(models.Model):
    MALE = (True, "Мужской")
    FEMALE = (False, "Женский")
    GENDERS = (MALE, FEMALE)

    first_name = models.CharField("Фамилия", max_length=50)
    middle_name = models.CharField("Имя", max_length=50)
    last_name = models.CharField("Отчество", max_length=50, null=True)
    date_of_birth = util.ModelDateField("Дата рождения")
    gender = models.BooleanField("Пол", choices=GENDERS)
    phone = models.CharField("Телефон", max_length=15, null=True, blank=True)

    class Meta:
        db_table = 'person'
        verbose_name = "Персона"
        verbose_name_plural = "Персоны"

    def get_fio(self):
        try:
            return (f'{self.first_name} {self.middle_name[0]}. ' + self.last_name[0] if self.last_name else "").strip()
        except:
            return ""

    def __str__(self):
        return " ".join([self.get_fio(), self.date_of_birth.__str__()])


class Client(models.Model):
    person = models.OneToOneField(Person, models.DO_NOTHING, verbose_name="Персона")
    pasport = models.OneToOneField(
        Pasport, on_delete=models.DO_NOTHING, verbose_name="Паспорт"
    )

    class Meta:
        db_table = 'client'
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"

    def get_fio(self):
        return self.person.get_fio()
    def __str__(self) -> str:
        return f"{self.person}, паспорт {self.pasport}"


class Employee(AbstractUser):
    person = models.OneToOneField(Person, models.DO_NOTHING, verbose_name="Персона")

    first_name = None
    last_name = None

    class Meta:
        db_table = 'employee'
        verbose_name = "Работник"
        verbose_name_plural = "Работники"

    def get_fio(self):
        return self.person.get_fio()

    def get_groups(self):
        return ", ".join([o.name for o in self.groups.all()])

    def __str__(self) -> str:
        return f"{self.get_fio()} {self.get_groups()}"


class PersonInsurance(models.Model):
    person = models.OneToOneField(Person, models.DO_NOTHING, verbose_name="Персона")
    pasport = models.OneToOneField(
        Pasport, on_delete=models.DO_NOTHING, verbose_name="Паспорт"
    )

    class Meta:
        db_table = 'personinsurance'
        verbose_name = "Субъект страхования"
        verbose_name_plural = "Субъекты страхования"


class House(models.Model):
    square = models.FloatField("Площадь")
    address = models.CharField("Адрес", max_length=250)
    scan_tech_plan = models.FileField(
        upload_to="scans/%Y/%m/%d/",
        verbose_name="Скан технического плана",
        validators=[
            FileExtensionValidator(
                ["pdf", "PDF"], "Поддерждиваются только PDF файлы", 400
            )
        ],
    )

    scan_doc_owner = models.FileField(
        upload_to="scans/%Y/%m/%d/",
        verbose_name="Скан документа на владение",
        validators=[
            FileExtensionValidator(
                ["pdf", "PDF"], "Поддерждиваются только PDF файлы", 400
            )
        ],
    )

    class Meta:
        db_table = 'house'
        verbose_name = "Недвижимость"
        verbose_name_plural = "Недвижимости"


class Contract(models.Model):
    client = models.ForeignKey(
        Client, on_delete=models.DO_NOTHING, verbose_name="Клиент"
    )

    status = models.CharField(choices=ContractStatuses, verbose_name="Статус")

    date_created = util.ModelDateField("Дата создания", auto_now_add=True)

    period = models.SmallIntegerField(
        "Срок страхования (в годах)",
        validators=[
            MinValueValidator(1, "Страхование производится минимум на год"),
            MaxValueValidator(100, "Слишком большой срок страхования"),
        ],
    )

    contract_type = models.CharField(choices=ContractTypes, verbose_name="Тип договора")

    cost = models.DecimalField(
        "Стоимость договора",
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(0, "Стоимость договора слишком мала")],
    )

    insurance_sum = models.DecimalField(
        "Страховая сумма",
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(100, "Страховая сумма слишком мала")],
    )

    scan = models.FileField(
        upload_to="pasport/%Y/%m/%d/",
        verbose_name="Скан договора",
        null=True, # Для того чтобы проще было делать форму заключения договора
        blank=True, 
        validators=[
            FileExtensionValidator(
                ["pdf", "PDF"], "Поддерждиваются только PDF файлы", 400
            )
        ],
    )

    insurance_object_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.DO_NOTHING,
        verbose_name="Вид объека (субъекта) страхования",
        limit_choices_to=(
            Q(app_label="work") & (Q(model="house") | Q(model="personinsurance"))
        ),
    )

    insurance_object_id = models.PositiveIntegerField()
    insurance_object = GenericForeignKey(
        "insurance_object_content_type", "insurance_object_id"
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.DO_NOTHING,
        verbose_name="Сотрудник, заключивший договор",
    )

    def __str__(self):
        return f"№{self.id}, {self.get_contract_type_display()}, {self.client}"

    class Meta:
        db_table = 'contract'
        verbose_name = "Договор страхования"
        verbose_name_plural = "Договоры страхования"


class IncidentDecision(models.Model):
    result = models.BooleanField(
        "Решение", choices=((True, "Случай страховой"), (False, "Случай НЕ страховой"))
    )

    sum = models.DecimalField(
        "Сумма страховой выплаты", max_digits=20, decimal_places=2
    )

    content = models.TextField("Основание")

    employee = models.ForeignKey(
        Employee,
        on_delete=models.DO_NOTHING,
        verbose_name="Работник, принявший решение по инциденту",
    )

    datetime_of_decision = util.ModelDateField("Дата принятия решения", auto_now_add=True)

    class Meta:
        db_table = 'incidentdecision'
        verbose_name = "Решение по инциденту"
        verbose_name_plural = "Решения по инцидентам"


class TicketIncident(models.Model):

    contract = models.ForeignKey(
        Contract, on_delete=models.DO_NOTHING, verbose_name="Договор страхования"
    )

    employee = models.ForeignKey(
        Employee, on_delete=models.DO_NOTHING, verbose_name="Работник, принявший заявку"
    )

    date_created = util.ModelDateField("Дата создания заявки", auto_now_add=True)
    content = models.TextField("Содержание")

    proofs = models.FileField("Подтверждающие документы", upload_to="docs/%Y/%m/%d/")
    decision = models.ForeignKey(IncidentDecision, models.CASCADE, null=True)

    class Meta:
        db_table = 'ticketincident'
        verbose_name = "Заявка об инциденте"
        verbose_name_plural = "Заявки об инцидентах"

##########
#
# Вспомогательные функции для моделей
#
##########

def to_year_fraction(date_: date):
    def sinceEpoch(date__):
        return time.mktime(date__.timetuple())

    s = sinceEpoch

    year = date_.year
    startOfThisYear = datetime.datetime(year=year, month=1, day=1)
    startOfNextYear = datetime.datetime(year=year + 1, month=1, day=1)

    yearElapsed = s(date_) - s(startOfThisYear)
    yearDuration = s(startOfNextYear) - s(startOfThisYear)
    fraction = yearElapsed / yearDuration

    return date_.year + fraction


def calculate_cost(
    contract_type: str, insurance_sum, years, **params
):
    result = 0
    match contract_type:
        case "house":
            square = params["square"]
            coef_years = years ** (1 / 3)
            coef_insurance_sum = 1 - 1 / math.log2(insurance_sum + 2)
            coef_square = 1 / (math.sqrt(square) ** - math.pow(square,  1 / 10))
            result = insurance_sum * coef_years * coef_insurance_sum * coef_square
        case "personinsurance":
            age = to_year_fraction(date.today()) - to_year_fraction(
                params["date_of_birth"]
            )
            coef_age = math.log(age / 20)
            coef_gender = 0.2 if params["gender"] == Person.MALE else 0.15
            coef_years = years ** (1 / 3)
            coef_insurance_sum = 1 - 1 / math.log2(insurance_sum + 2)
            result = insurance_sum * coef_age * coef_gender * coef_years
        case _:
            raise Exception(f"Передан неизвестный вид страхован {contract_type}")
    return round(result, 2)