from typing import Any

from django.core.files.base import ContentFile
from django.db.models.query import QuerySet
from django.db.models import *
from django.db import connection
from django.utils.decorators import method_decorator
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, View
from django.shortcuts import render

from .forms import *
from .models import Contract

from dateutil.relativedelta import relativedelta
import pdfkit


# Главная страница
@login_required(login_url="home")
def work(request: HttpRequest):
    return render(request, "work/index.html")


# Представление отправки уведомлений
@method_decorator(util.one_of_group_required(["manager", "worker"]), "dispatch")
class Notifications(View):

    template_name = "work/send_notifications.html"

    def get(self, request: HttpRequest):
        context = {"form": NotificationsForm()}
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest):
        form = NotificationsForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, context={"form": form})

        try:
            interval = form.cleaned_data["interval"]
            today = date.today()
            expected_date = today + interval
            counter = 0
            for contract in Contract.objects.all():
                contract_expires = contract.date_created + relativedelta(
                    years=contract.period
                )
                if contract_expires == expected_date:
                    self.send_notification(contract)
                    counter += 1

            util.set_toast(
                "success", f"Извещения успешно отправлены (количество = {counter})."
            )
            context = {"form": NotificationsForm()}
            return render(request, self.template_name, context)
        except Exception as e:
            util.set_toast("error", f"Ошибка отправки уведомлений. Подробности: {e}")
            return render(request, self.template_name, context={"form": form})

    # Здесь теоретически нужно было бы отправлять уведомление
    def send_notification(self, contract: Contract):
        pass


# Представление создания заявки об инциденте
@method_decorator(util.one_of_group_required(["manager", "worker"]), "dispatch")
class NewTicketIncident(View):

    template_name = "work/several_forms_template.html"

    def get(self, request: HttpRequest):
        context = {
            "forms": [NewTicketForm()],
            "multipart": True,
            "names": ["Заявка об инциденте"],
        }
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest):
        form = NewTicketForm(request.POST, request.FILES)
        context = {
            "forms": [form],
            "multipart": True,
            "names": ["Заявка об инциденте"],
        }

        if not form.is_valid():
            return render(request, self.template_name, context)

        try:
            obj = form.save(commit=False)
            obj.employee = request.user
            obj.save()

            util.set_toast("success", "Заявка успешно создана")
            context = {
                "forms": [NewTicketForm()],
                "multipart": True,
                "names": ["Заявка об инциденте"],
            }
            return render(request, self.template_name, context)
        except Exception as e:
            util.set_toast("error", f"Заявка не создана. Подробности: {e}")
            return render(request, self.template_name, context)


# Представление принятия решения по заявке
@method_decorator(util.one_of_group_required(["manager", "expert"]), "dispatch")
class ResolveTicketIncidentView(View):

    template_name = "work/resolve_ticket.html"

    def get(self, request: HttpRequest, id: int):
        context = {}
        try:
            ticket = TicketIncident.objects.get(id=id)
            form = IncidentDecisionForm()
            context = {"ticket": ticket, "form": form}
        except Exception as e:
            util.set_toast(
                "error", f"При загрузке страницы возникла ошибка. Подробности: {e}"
            )
        finally:
            return render(request, self.template_name, context)

    def post(self, request: HttpRequest, id: int):
        context = {}
        try:
            ticket = TicketIncident.objects.get(id=id)
            form = IncidentDecisionForm(request.POST)
            if not form.is_valid():
                context = {"ticket": ticket, "form": form}
                util.set_toast("error", "Проверьте правильность введенных данных")
                transaction.rollback()
                return render(request, self.template_name, context)

            with transaction.atomic():
                decision = form.instance
                decision.employee = request.user
                decision.save()
                ticket.decision = decision
                ticket.save()
            transaction.commit()
            util.set_toast("success", "Решение по заявке успешно сохранено")
            return redirect(reverse("not_resolved_tickets"))
        except Exception as e:
            transaction.rollback()
            util.set_toast(
                "error", f"При загрузке страницы возникла ошибка. Подробности: {e}"
            )
            return render(request, self.template_name, context)


# Эндпоинт расторжения договора
@util.one_of_group_required(["manager", "worker"])
def terminate_contract(request: HttpRequest, id: int):
    try:
        contract = Contract.objects.get(id=id)
        if contract.status != "terminated":
            util.set_toast("error", "Можно расторгнуть только активный договор")
        else:
            contract.status = "terminated"
            contract.save()
            util.set_toast("success", "Договор успешно расторгнут")
    except Exception as e:
        util.set_toast("error", f"Договор не расторгнут. Подробности: {e}")
    finally:
        return redirect(reverse("contracts_list"))


# Представление просмотра списка договоров
class ContractListView(ListView):
    model = Contract
    template_name = "work/contract_list.html"
    context_object_name = "contracts"


# Преставление просмотра списка активных заявок
@method_decorator(
    util.one_of_group_required(["manager", "worker", "expert"]), "dispatch"
)
class NotResolvedTicketsListView(ListView):
    model = TicketIncident
    template_name = "work/not_resolved_tickets_list.html"
    context_object_name = "tickets"

    def get_queryset(self) -> QuerySet[Any]:
        return TicketIncident.objects.filter(decision__isnull=True)


# Представление запроса финансового отчета
@method_decorator(util.one_of_group_required(["manager"]), "dispatch")
class FinanceReport(View):

    template_name = "work/finance_report.html"

    def get_report_data(self, data: dict) -> dict:
        new_contracts = Contract.objects.filter(
            Q(date_created__gte=data["start"]) & Q(date_created__lte=data["end"])
        )
        decisions = IncidentDecision.objects.filter(
            Q(datetime_of_decision__gte=data["start"])
            & Q(datetime_of_decision__lte=data["end"])
            & Q(result=True)
        )

        count_of_new_contracts = new_contracts.count()
        profit = new_contracts.aggregate(result=Sum("cost"))["result"]
        profit = 0 if profit is None else profit
        count_of_decisions = decisions.count()
        waste = decisions.aggregate(result=Sum("sum"))["result"]
        waste = 0 if waste is None else waste

        total = profit - waste
        return {
            **data,
            "contracts": count_of_new_contracts,
            "incidents": count_of_decisions,
            "profit": profit,
            "waste": waste,
            "total": total,
        }

    def render_report(self, context: dict) -> HttpResponse:
        config = pdfkit.configuration(
            wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe"
        )
        rendered_template = render(
            self.request, "docs/finance_report.html", context
        ).content.decode()
        rendered_pdf = pdfkit.from_string(rendered_template, configuration=config)

        filename = f"{'Подробный' if context['is_detailed'] else 'Краткий'} отчет за период с {context['start']} по {context['end']}.pdf"

        file_to_send = ContentFile(rendered_pdf)
        response = HttpResponse(file_to_send, "application/pdf")
        response["Content-Length"] = file_to_send.size
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    def get(self, request: HttpRequest):
        return render(
            request, self.template_name, context={"form": FinanceReportForm()}
        )

    def post(self, request: HttpRequest):
        form = FinanceReportForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, context={"form": form})

        context = self.get_report_data(form.cleaned_data)
        return self.render_report(context)


# Представление запроса рискового отчета
@method_decorator(util.one_of_group_required(["manager"]), "dispatch")
class RiskReport(View):

    template_name = "work/risk_report.html"

    def get_report_data(self, data: dict) -> dict:
        start = data["start"]
        end = data["end"]

        report_data = list(
            Contract.objects.filter(date_created__gte=start)
            .filter(date_created__lte=end)
            .values("contract_type")
            .annotate(count=Count("id"))
            .annotate(insurance_sums=Sum("insurance_sum"))
            .order_by("contract_type")
        )

        decisions = list(
            TicketIncident.objects.select_related("decision")
            .filter(decision__datetime_of_decision__gte=start)
            .filter(decision__datetime_of_decision__lte=end)
            .filter(decision__result=True)
            .values("contract__contract_type")
            .annotate(sums=Sum("decision__sum"))
            .order_by("contract__contract_type")
        )

        report_data = [
            {
                **c,
                "sums": (
                    d["sums"]
                    if c["contract_type"] == d["contract__contract_type"]
                    else 0
                ),
            }
            for c in report_data
            for d in decisions
        ]

        return {**data, "data": report_data}

    def render_report(self, context: dict) -> HttpResponse:
        config = pdfkit.configuration(wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")
        rendered_template = render(
            self.request, "docs/risk_report.html", context
        ).content.decode()
        rendered_pdf = pdfkit.from_string(rendered_template, configuration=config)

        filename = f"Рисковый отчет за период с {context['start']} по {context['end']}.pdf"

        file_to_send = ContentFile(rendered_pdf)
        response = HttpResponse(file_to_send, "application/pdf")
        response["Content-Length"] = file_to_send.size
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    def get(self, request: HttpRequest):
        return render(request, self.template_name, context={"form": RiskReportForm()})

    def post(self, request: HttpRequest):
        form = RiskReportForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, context={"form": form})

        data = form.cleaned_data
        context = self.get_report_data(data)
        return self.render_report(context)

