from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from . import models


admin.site.register(models.Pasport)
admin.site.register(models.Person)
admin.site.register(models.Client)
admin.site.register(models.PersonInsurance)
admin.site.register(models.House)
admin.site.register(models.Contract)
admin.site.register(models.IncidentDecision)
admin.site.register(models.TicketIncident)


@admin.register(models.Employee)
class EmployeeAdminModel(admin.ModelAdmin):

    def save_model(self, request, obj, form, change):
        print(1)
        if obj.pk:
            print(2)
            orig_obj = models.Employee.objects.get(pk=obj.pk)
            if obj.password != orig_obj.password:
                obj.set_password(obj.password)
        else:
            print(3)
            obj.set_password(obj.password)
            print(4)
        obj.save()