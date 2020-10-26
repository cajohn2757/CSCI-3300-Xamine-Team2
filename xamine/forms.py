from django import forms
from django.http import HttpResponseRedirect
from django.shortcuts import render
from colorful.fields import RGBColorField
from intl_tel_input.widgets import IntlTelInputWidget
from xamine.models import Patient, Order, Image, MedicationOrder, MaterialOrder, ColorScheme

from bootstrap_datepicker_plus import DatePickerInput, DateTimePickerInput

yesnoch = (
    (False, 'No'),
    (True, 'Yes'),
)


class PatientInfoForm(forms.ModelForm):
    """ Handles creation and updating of Patient model """

    class Meta:
        model = Patient
        fields = [
            'first_name', 'middle_name', 'last_name', 'email_info', 'birth_date', 'phone_number',
            'card_type', 'card_number', 'card_owner', 'card_CVV', 'card_expiration_date',
            'allergy_asthma', 'allergy_xraydye', 'allergy_mridye', 'allergy_latex', 'notes'
            ]

        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'email_info': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'birth_date': DatePickerInput(format='%Y-%m-%d', options={"useCurrent": False},
                                          attrs={'placeholder': 'YYYY-MM-DD'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control input-phone', 'autocomplete': 'off'}),

            'card_type': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'card_number': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off', 'type': 'password'}),
            'card_owner': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'card_CVV': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'card_expiration_date': DatePickerInput(format='%Y-%m-%d', options={"useCurrent": False},
                                                    attrs={'placeholder': 'YYYY-MM'}),
            'allergy_asthma': forms.Select(attrs={'class': 'form-control'}, choices=yesnoch),
            'allergy_xraydye': forms.Select(attrs={'class': 'form-control'}, choices=yesnoch),
            'allergy_mridye': forms.Select(attrs={'class': 'form-control'}, choices=yesnoch),
            'allergy_latex': forms.Select(attrs={'class': 'form-control'}, choices=yesnoch),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'autocomplete': 'off', 'rows': '3'}),
        }


class ScheduleForm(forms.ModelForm):
    """ Handles scheduling of Orders """

    class Meta:
        model = Order
        fields = ['appointment']

        widgets = {
            'appointment': DateTimePickerInput(format='%Y-%m-%d %I:%M %p', options={"useCurrent": True},
                                               attrs={'placeholder': 'mm/dd/yyyy'})
        }


class TeamSelectionForm(forms.ModelForm):
    """ Handles selection of our team for each order """
    class Meta:
        model = Order
        fields = ['team']

        widgets = {
            'team': forms.Select(attrs={'class': 'form-control'})
        }


class AnalysisForm(forms.ModelForm):
    """ Handles submission and saving of radiology report """
    class Meta:
        model = Order
        fields = ['report']

        widgets = {
            'report': forms.Textarea(attrs={'class': 'form-control', 'autocomplete': 'off', 'rows': '6'}),
        }


class ImageUploadForm(forms.ModelForm):
    """ Handles Image uploading """

    class Meta:
        model = Image
        fields = ['label', 'image', 'order']

        widgets = {
            'label': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'image': forms.FileInput(attrs={'allow_empty_file': 'off', 'max_length': '50', 'class': 'custom-file-input',}),
            'order': forms.HiddenInput(),
        }


class PatientLookupForm(forms.ModelForm):
    """ Handles patient lookup """
    class Meta:
        model = Patient
        fields = ['birth_date']

        widgets = {
            'birth_date': DatePickerInput(format='%Y-%m-%d', options={"useCurrent": False},
                                          attrs={'placeholder': 'YYYY-MM-DD'}),
        }


class NewOrderForm(forms.ModelForm):
    """ Handles creation of new order """

    class Meta:
        model = Order
        fields = ['patient', 'visit_reason', 'imaging_needed', 'modality', 'notes']

        widgets = {
            'patient': forms.HiddenInput(),
            'visit_reason': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'imaging_needed': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'modality': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'autocomplete': 'off', 'rows': '3'}),
        }


class MedicationOrderForm(forms.ModelForm):
    """ Handles Patient Medication Prescription Inputs """

    class Meta:
        model = MedicationOrder
        fields = ['order', 'name', 'quantity', 'price', 'billed']

        widgets = {
            'order': forms.HiddenInput(),
            'name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'on'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'billed': forms.HiddenInput(),
        }


class MaterialOrderForm(forms.ModelForm):
    """ Handles Patient Material Usage Inputs """

    class Meta:
        model = MaterialOrder
        fields = ['order', 'material', 'quantity', 'price', 'billed']

        widgets = {
            'order': forms.HiddenInput(),
            'material': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'billed': forms.HiddenInput(),
        }


class ColorSchemeForm(forms.ModelForm):
    """Handles ColorScheme Inputs"""

    class Meta:
        model = ColorScheme
        fields = ['mainTheme', 'mainPrimary', 'mainSecondary']

        widgets = {
            'mainTheme': RGBColorField(colors=['#FF0000', '#00FF00', '#0000FF']),
            'mainPrimary': RGBColorField(colors=['#FF0000', '#00FF00', '#0000FF']),
            'mainSecondary': RGBColorField(colors=['#FF0000', '#00FF00', '#0000FF'])
        }
