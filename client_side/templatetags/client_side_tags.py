from django import template


register = template.Library() 

@register.inclusion_tag('client/menu_tag.html', takes_context=True)
def show_client_menu(context):
    tabs = {
        "home": "Главная",
        "contract_types": "Виды страхования",
        "contacts": "Контакты", 
        "about": "О компании"
    }
    r = context["request"]
    selected_url_name = r.resolver_match.url_name
    return {
        "tabs": [(k, v) for k, v in tabs.items()],
        "selected": (selected_url_name, tabs.get(selected_url_name, None))
    }