from django.contrib import admin

from .models import Inbox, Choice

#admin.site.register(Inbox)
#admin.site.register(Choice)


class ChoiceInLine(admin.TabularInline):
    model = Choice
    extra = 2


@admin.register(Inbox)
class QuestionAdmin(admin.ModelAdmin):
    fieldsets = [(None, {'fields': ['patient_name']}), ('Date Information', {'fields': ['pub_date'], 'classes': ['collapse']}),]
    inlines = [ChoiceInLine]

