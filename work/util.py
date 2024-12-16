from functools import wraps
from typing import Any, Callable
from django.shortcuts import redirect, render
from django.http import HttpResponseForbidden
from django.urls import reverse

from django import forms
from django.db import models
from formtools.wizard.views import CookieWizardView
from django.utils.decorators import classonlymethod

toast_data = {}
def set_toast(result, message):
    toast_data['result'] = result
    toast_data['message'] = message

def get_toast():
    global toast_data
    v = {**toast_data}
    toast_data = {}
    return v


class DateInput(forms.DateInput):
    input_type = 'date'


class ModelDateField(models.DateField):
    widget = DateInput()


class FormDateField(forms.DateField):
    widget = DateInput()

###################
#
#    Декораторы
#
###################

def one_of_group_required(groups: list[str] | str, permision_denied_template_path: str = None):
    '''
    Декоратор для допуска к представлению только пользователей, состоящих в переданных группах
    '''

    if type(groups) == str:
        groups = [groups]
    elif type(groups) != list:
        raise ValueError()
    
    def _check_group(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_anonymous:
                return redirect(reverse('login'))
            if not (request.user.groups.filter(name__in=groups).exists() or request.user.is_superuser):
                if permision_denied_template_path is not None:
                    return render(request, permision_denied_template_path)
                else:
                    return HttpResponseForbidden()
            return view_func(request, *args, **kwargs)
        return wrapper
    return _check_group


def super_user_required(permision_denied_template_path: str = None):
    '''
    Декоратор для допуска к представлению только супер-пользователей
    '''
    
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if not permision_denied_template_path:
                return HttpResponseForbidden()
            return render(request, permision_denied_template_path)
        return wrapper
    return decorator


class FormItem:

    __counter = 0

    def __init__(
        self,
        form: forms.Form,
        name: str | None = None,
        condition: Callable | bool = True,
        **extra_context
    ):
        if name:
            self.name = name
        else:
            self.name = str(self.__class__.__counter)
            self.__class__.__counter += 1 

        self.form = form
        self.condition = condition
        self.extra_context = extra_context

    def to_wizard_format(self) -> tuple[forms.Form, str | None, Callable | bool, dict]:
        return (self.form, self.name, self.condition, self.extra_context)


class CustomWizardView(CookieWizardView):

    FORMS: list[FormItem] = []

    template_name = "work/wizard_form.html"
    prefix: str = None
    form_list = [forms.Form] # Fake item for pass assert in WizardView
    condition_dict = {}
    instance_dict = {}
    extras = {}
    multipart: bool = False

    @classmethod
    def resolve_step_name(cls, name_without_prefix) -> str:
        return cls.prefix + "_" + name_without_prefix

    @classonlymethod
    def as_view(cls, **initkwargs):
        cls.form_list.clear()
        if cls.prefix is None:
            cls.prefix = cls.__name__
        for item in cls.FORMS:
            form, name, cond, extra = item.to_wizard_format()
            pref_name = cls.resolve_step_name(name)
            cls.form_list.append((pref_name, form))
            cls.condition_dict[pref_name] = cond
            cls.extras[pref_name] = extra

        tmp = cls.instance_dict
        cls.instance_dict = {}
        for name, instance in tmp.items():
            cls.instance_dict[cls.resolve_step_name(name)] = instance
        return super(__class__, cls).as_view(**initkwargs)
    

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context['multipart'] = self.__class__.multipart
        extra = __class__.extras[self.steps.current]
        context.update({"extra": extra})
        return context
    

class AdaptiveWideTableStyleMixin(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs["class"] = "d-flex col-8"
            # if name in self.Meta.readonly_fields:
            #     field.disabled = True 
            #     field.widget.attrs['class'] = field.widget.attrs['class'] + " disabled"


class ReadOnlyMixin(forms.Form):

    readonly: str | list[str] = '__all__'
    exclude: list[str] = []

    def __init__(self, *args, **kwargs):
        super(__class__, self).__init__(*args, **kwargs)
        if type(self.__class__.readonly) == str:
            if self.__class__.readonly == '__all__':
                for name, field in self.fields.items():
                    if name not in self.__class__.exclude:
                        field.disabled = True
            else:
                raise Exception("Список readonly заполнен неверно.")
            
        elif type(self.__class__.readonly) in (list, tuple):
            for field in self.__class__.readonly:
                if field not in self.__class__.exclude:
                    self.fields[field].disabled = True


class CustomFileInput(forms.widgets.ClearableFileInput):
    def __init__(self, media_url, attrs = None):
        self.media_url = media_url
        super().__init__(attrs)
    def get_context(self, name: str, value: Any, attrs: dict[str, Any] | None) -> dict[str, Any]:
        if self.media_url is None:
            raise Exception("Не установлен MEDIA_ROOT")
        class tmp:
            def __init__(self, file, media_url):
                self.file = file
                self.url = media_url + file.name
            
            def __str__(self) -> str:
                return self.file.name
        context = super().get_context(name, value, attrs)
        context['widget']['value'] = tmp(value, self.media_url)
        context['widget']['is_initial'] = True
        return context