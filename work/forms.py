import os
from django import forms
from django.shortcuts import redirect, render
from django.urls import reverse
from django.core.files.storage import FileSystemStorage
from insurance_company import settings
from .models import *
from .util import (
    AdaptiveWideTableStyleMixin,
    CustomFileInput,
    CustomWizardView,
    FormItem,
    ReadOnlyMixin,
)
from django.db import transaction
from betterforms.multiform import MultiModelForm
import pdfkit
import uuid
from django.core.files import File

from dateutil.relativedelta import relativedelta


# Форма создания новой заявки об инциденте
class NewTicketForm(AdaptiveWideTableStyleMixin, forms.ModelForm):
    class Meta:
        model = TicketIncident
        fields = '__all__'
        exclude = ['employee', 'decision']


# Форма создания паспорта
class PasportForm(AdaptiveWideTableStyleMixin, forms.ModelForm):
    class Meta:
        model = Pasport
        fields = "__all__"


# Форма создания персоны
class PersonForm(AdaptiveWideTableStyleMixin, forms.ModelForm):
    class Meta:
        model = Person
        fields = "__all__"


# Форма создания клиента
class ClientWizardForm(CustomWizardView):

    file_storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, "tmp"))
    multipart = True

    FORMS = [
        FormItem(PersonForm, "person", title="Персональные данные"),
        FormItem(PasportForm, "pasport", title="Паспортные данные"),
    ]

    def done(self, form_list, form_dict, **kwargs):
        try:
            with transaction.atomic():
                person = form_dict[__class__.resolve_step_name("person")].save()
                pasport = form_dict[__class__.resolve_step_name("pasport")].save()
                client = Client(person=person, pasport=pasport)
                client.save()
                transaction.commit()
            util.set_toast("success", "Клиент успешно добавлен в базу.")
        except Exception as e:
            transaction.rollback()
            util.set_toast("error", f"Ошибка при выполнении операции. Подробности: {e}")
        finally:
            return redirect(reverse("work"))


# Форма заполнения данных о контракте
class ContractForm(AdaptiveWideTableStyleMixin, forms.ModelForm):
    class Meta:
        model = Contract
        fields = "__all__"
        exclude = [
            "status",
            "cost",
            "insurance_object_id",
            "employee",
            "scan",
            "insurance_object_content_type",
            "contract_type",
        ]


# Форма создания недвижимости
class HouseForm(AdaptiveWideTableStyleMixin, forms.ModelForm):
    class Meta:
        model = House
        fields = "__all__"


# Форма создания человека как субъекта страхования
class PersonInsuranceForm(MultiModelForm):
    form_classes = {"person": PersonForm, "pasport": PasportForm}
    base_fields = {}


# Форма скачивания печатной формы договора
class DownloadContractForm(AdaptiveWideTableStyleMixin, ReadOnlyMixin, forms.Form):
    file_ = forms.FileField(
        label="Ссылка на форму печати договора",
        widget=CustomFileInput(settings.MEDIA_URL),
    )
    signed_contract = forms.FileField(label="Подписанный скан договора (который выше)")
    exclude = ["signed_contract"]


# Форма просмотра расчитанной стоимости договора
class ContractPreviewForm(AdaptiveWideTableStyleMixin, ReadOnlyMixin, forms.Form):
    cost = forms.DecimalField(label="Стоимость")


# Пошаговая форма создания договора
class ContractWizardForm(CustomWizardView):
    file_storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, "tmp"))
    multipart = True
    instance_dict = {
        "contract": Contract(),
        "pasport": Pasport(),
        "person": Person(),
        "house": House(),
    }

    def house_selected(self):
        data = self.get_form_initial("contract")
        item = data.get("contract_type", None)
        return item == 'house'

    def person_selected(self):
        data = self.get_form_initial("contract")
        item = data.get("contract_type", None)
        return item == 'personinsurance'

    def fill_common_params(self, data: dict) -> dict:
        contract = __class__.TMP_DATA["contract"]
        data["insurance_sum"] = float(contract.insurance_sum)
        data["years"] = contract.period
        return data

    def fill_house(self, data) -> dict:
        data["contract_type"] = 'house'
        data["square"] = __class__.TMP_DATA['house'].square
        return data
    
    def fill_person(self, data) -> dict:
        data["contract_type"] = 'personinsurance'
        person = __class__.TMP_DATA['person']
        data["date_of_birth"] = person.date_of_birth
        data["gender"] = person.gender
        return data

    FORMS = [
        FormItem(ContractForm, "contract", title="Заключение нового договора"),
        FormItem(
            PersonForm,
            "person",
            title="Данные о страхуемом человеке",
            condition=person_selected,
        ),
        FormItem(
            PasportForm,
            "pasport",
            title="Паспортные данные страхуемого человека",
            condition=person_selected,
        ),
        FormItem(
            HouseForm,
            "house",
            title="Информация о недвижимости",
            condition=house_selected,
        ),
        FormItem(
            ContractPreviewForm, "preview", title="Просмотр рассчитанной стоимости"
        ),
        FormItem(
            DownloadContractForm,
            "download_form",
            title="Договор для подписания",
        ),
    ]

    TMP_DATA = {}

    def process_step(self, form):
        if __class__.TMP_DATA.get('transaction', None) is None:
            transaction.set_autocommit(False)
            __class__.TMP_DATA['transaction'] = transaction.atomic()
        if self.steps.current == self.resolve_step_name('contract'):
            with __class__.TMP_DATA['transaction']:
                c = form.save(commit=False)
                c.employee = self.request.user
                c.status = 'active'
                __class__.TMP_DATA['contract'] = c
                __class__.TMP_DATA['data'] = self.fill_common_params({})
            
        elif self.steps.current == self.resolve_step_name('person'):
            with __class__.TMP_DATA['transaction']:
                __class__.TMP_DATA['person'] = form.save(commit=False)
                __class__.TMP_DATA['contract'].contract_type = 'personinsurance'

        elif self.steps.current == self.resolve_step_name('pasport') and self.person_selected():
            with __class__.TMP_DATA['transaction']:
                __class__.TMP_DATA['pasport'] = form.save(commit=False)
                data = self.fill_person(__class__.TMP_DATA['data'])
                __class__.TMP_DATA['contract'].cost = calculate_cost(**data)
                person = __class__.TMP_DATA['person']
                pasport = __class__.TMP_DATA['pasport']
                person_insurance = PersonInsurance(person=person, pasport=pasport)
                person.save()
                pasport.save()
                person_insurance.save()
                __class__.TMP_DATA['contract'].insurance_object = person_insurance
                __class__.TMP_DATA['contract'].save()

        elif self.steps.current == self.resolve_step_name('house') and self.house_selected():
            with __class__.TMP_DATA['transaction']:
                __class__.TMP_DATA['house'] = form.save(commit=False)
                __class__.TMP_DATA['contract'].contract_type = 'house'
                data = self.fill_house(__class__.TMP_DATA['data'])
                __class__.TMP_DATA['contract'].cost = calculate_cost(**data)
                __class__.TMP_DATA['house'].save()
                __class__.TMP_DATA['contract'].insurance_object = __class__.TMP_DATA['house']
                __class__.TMP_DATA['contract'].save()

        elif self.steps.current == self.resolve_step_name('download_form'):
            with __class__.TMP_DATA['transaction']:
                scan = form.cleaned_data['signed_contract']
                __class__.TMP_DATA['contract'].scan = scan
                __class__.TMP_DATA['contract'].save()

        return super().process_step(form)

    def get_form_initial(self, step):
        if step == self.resolve_step_name("preview"):
            return { 'cost': __class__.TMP_DATA['contract'].cost }

        elif step == self.resolve_step_name("download_form"):
            path_ = f"contracts/{uuid.uuid4()}.pdf"
            path = settings.MEDIA_ROOT / path_
            input = render(
                self.request, "docs/contract_form.html", {"contract": __class__.TMP_DATA['contract']}
            ).content
            config = pdfkit.configuration(
                wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe"
            )
            pdfkit.from_string(input.decode(), path, configuration=config)
            return {"file_": File(open(path, mode="rb"), path_)}

        return self.initial_dict.get(step, {})

    def done(self, form_list, form_dict, **kwargs):
        try:
            transaction.commit()
            util.set_toast("success", "Договор успешно сохранен.")
        except Exception as e:
            util.set_toast(
                "error", f"При сохранении договора возникла ошибка. Подробности: {e}"
            )
        finally:
            return redirect(reverse("work"))


# Форма принятия решения по заявке
class IncidentDecisionForm(AdaptiveWideTableStyleMixin, forms.ModelForm):
    class Meta:
        model = IncidentDecision
        fields = '__all__'
        exclude = ['employee', 'datetime_of_decision']


# Форма отправки уведомлений
class NotificationsForm(AdaptiveWideTableStyleMixin, forms.Form):

    def convert(value: str):
        return eval(value.replace('+', ''))

    def add_months(current_date, months_to_add):
        return datetime(current_date.year + (current_date.month + months_to_add - 1) // 12,
                            (current_date.month + months_to_add - 1) % 12 + 1,
                            current_date.day, current_date.hour, current_date.minute, current_date.second)

    INTERVALS = {
        relativedelta(days=1): "1 день",
        relativedelta(days=2): "2 дня",
        relativedelta(days=3): "3 дня",
        relativedelta(days=4): "4 дня",
        relativedelta(days=5): "5 дней",
        relativedelta(days=6): "6 дней",
        relativedelta(weeks=1): "1 неделю",
        relativedelta(weeks=2): "2 недели",
        relativedelta(months=1): "1 месяц",
        relativedelta(months=2): "2 месяца",
    }

    interval = forms.TypedChoiceField(choices=INTERVALS, coerce=convert, label="Отправить уведомления для договоров, которые истекут через")


# Форма выбора параметров финансового отчета
class FinanceReportForm(AdaptiveWideTableStyleMixin, forms.Form):
    start = util.FormDateField(label="Начало интервала")
    end = util.FormDateField(label="Конец интервала")

    def convert(val):
        return val != 'False'

    is_detailed = forms.fields.TypedChoiceField(coerce=convert, choices=((True, "Подробный"), (False, "Краткий")), label="Подробный ли нужен отчет?")

# Форма выбора параметров рискового отчета
class RiskReportForm(AdaptiveWideTableStyleMixin, forms.Form):
    start = util.FormDateField(label="Начало интервала")
    end = util.FormDateField(label="Конец интервала")