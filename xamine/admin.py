from django.contrib import admin

from xamine.models import Patient, Level, Order, Image, ModalityOption, Team, AppSetting, Material, MaterialOrder, MedicationOrder, ColorScheme, Balance, Insurance, Transaction

admin.site.site_header = 'Xamine RIS Admin'


class ImageInline(admin.TabularInline):
    model = Image
    fields = ['label', 'image', 'added_on', 'user']
    readonly_fields = ['added_on', 'user']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    readonly_fields = ['added_on', 'last_edit']
    inlines = [ImageInline]


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    filter_horizontal = ['radiologists', 'technicians']


admin.site.register(Patient)
admin.site.register(Level)
admin.site.register(AppSetting)
# admin.site.register(Image)
admin.site.register(ModalityOption)
admin.site.register(Material)
admin.site.register(MaterialOrder)
admin.site.register(Insurance)
admin.site.register(MedicationOrder)
admin.site.register(Balance)
admin.site.register(ColorScheme)
admin.site.register(Transaction)

