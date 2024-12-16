from django import template
from django.http import HttpRequest

register = template.Library()

@register.filter
def pop_var(session, name):
    try:
        val = session.pop(name, None)
        return val
    except:
        return None


@register.filter
def list_get(list, index):
    try:
        return list[index]
    except:
        return None


@register.filter
def get_type(value):
    return type(value).__name__


@register.filter
def startswith(value, arg):
    try:
        return value.startswith(arg)
    except:
        return None


@register.filter(name="has_group")
def has_group(user, group_name: str = None):
    return (
        group_name is None
        or user.is_superuser
        or user.groups.filter(name=group_name).exists()
    )


@register.inclusion_tag("work/menu_tag.html", takes_context=True)
def show_work_menu(context):
    from ..util import get_toast

    tabs = {
        "work": "Главная",
        "_": {
            "title": "Заключение нового договора",
            "items": {
                "new_house_contract": "Страхование недвижимости",
                "new_person_contract": "Страхование человека",
            },
        },
        "__": {
            "title": "Заявки",
            "items": {
                "new_incident_ticket": "Заявка об инциденте",
                "not_resolved_tickets": "Рассмотрение инцидента",
                '-': None,
                "contracts_list": "Расторгнуть договор",
            },
        },
        "new_client": "Регистрация нового клиента",
        'send_notifications': "Отправка извещений",
        '___': {
            'title': "Формирование отчетности",
            'items': {
                "finance_report": "Финансовый отчет",
                "risk_report": "Рисковый отчет"
            }
        }
    }
    request: HttpRequest = context["request"]
    toast = get_toast()
    selected_url_name = request.resolver_match.url_name
    return {
        "tabs": tabs,
        "selected": selected_url_name,
        **context.flatten(),
        "toast": toast
    }
