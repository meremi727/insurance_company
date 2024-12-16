from django.urls import path

from . import views, forms, models


urlpatterns = [
    path("", views.work, name="work"),
    path('new_client', forms.ClientWizardForm.as_view(), name='new_client'),
    path("new_person_contract", forms.ContractWizardForm.as_view(initial_dict={"contract": {"contract_type": 'personinsurance'}}), name="new_person_contract"),
    path("new_house_contract", forms.ContractWizardForm.as_view(initial_dict={"contract": {"contract_type": 'house'}}), name="new_house_contract"),
    path("new_incident_ticket", views.NewTicketIncident.as_view(), name="new_incident_ticket"),
    path('not_resolved_tickets', views.NotResolvedTicketsListView.as_view(), name='not_resolved_tickets'),
    path("resolve_incident_ticket/<int:id>", views.ResolveTicketIncidentView.as_view(), name="resolve_incident_ticket"),
    path("terminate_contract/<int:id>", views.terminate_contract, name="terminate_contract"),
    path("contracts_list", views.ContractListView.as_view(), name="contracts_list"),
    path("send_notifications", views.Notifications.as_view(), name="send_notifications"),
    path("finance_report", views.FinanceReport.as_view(), name="finance_report"),
    path("risk_report", views.RiskReport.as_view(), name="risk_report")
]
