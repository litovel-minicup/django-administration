# coding=utf-8
from django.contrib import admin, messages
from django.db.models import QuerySet
from django.forms import TextInput, Textarea
from django.forms.models import ModelForm
from django.utils.html import format_html
from django.utils.translation import ugettext as _

from minicup_model.core.models import Photo
from .models import TeamInfo, MatchTerm, Match, Tag


def swap(model_admin: admin.ModelAdmin, request, queryset: QuerySet):
    if queryset.count() != 2:
        model_admin.message_user(request, _('Swapped can be only directly two matches.'), level=messages.ERROR)
        return

    first, second = queryset  # type: Match, Match
    first.match_term, second.match_term = second.match_term, first.match_term
    first.save(update_fields=['match_term', ])
    second.save(update_fields=['match_term', ])
    model_admin.message_user(request, _('Successfully swapped.'), level=messages.SUCCESS)


swap.short_description = _('Swap terms of two selected matches.')


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    date_hierarchy = 'match_term__day__day'
    list_filter = (
        'match_term__day__year__slug',
        'category__name',
    )

    list_display = (
        '__str__',
        'category',
        'match_term'
    )

    search_fields = (
        'match_term__start',
        'category__name',
        'home_team_info__name',
        'away_team_info__name',
    )

    actions = [swap, ]

    class MatchForm(ModelForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if self.instance and self.instance.category:
                self.fields['match_term'].queryset = MatchTerm.objects.filter(
                    day__year=self.instance.category.year
                )

        class Meta:
            model = Match
            fields = '__all__'

    form = MatchForm


@admin.register(TeamInfo)
class TeamInfoAdmin(admin.ModelAdmin):
    list_filter = (
        'category__year',
        'category__name',
    )
    list_display = (
        '__str__',
        'slug',
        'tag',
        'player_count',
        'photo_count',
    )

    class form(ModelForm):
        class Meta:
            model = Photo
            fields = '__all__'
            widgets = dict(
                password=Textarea(attrs=dict(rows=1)),
                # active=CheckboxInput,
            )


@admin.register(MatchTerm)
class MatchTermAdmin(admin.ModelAdmin):
    date_hierarchy = 'day__day'

    list_filter = (
        # 'day__year'
    )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    # date_hierarchy = 'year'

    list_display = (
        '__str__',
        'photo_count',
        'is_main',
    )

    list_filter = (
        'year',
        'is_main',
    )


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    # date_hierarchy = 'year'
    class form(ModelForm):
        class Meta:
            model = Photo
            fields = '__all__'
            widgets = dict(
                filename=TextInput,
                author=TextInput,
                # active=CheckboxInput,
            )

    list_display = (
        '__str__',
        'added',
        'taken',
        'tag_count',
        'image'
    )

    readonly_fields = ('filename',)

    list_filter = (
        'photo_tag_photo__tag__year',
    )

    def has_delete_permission(self, request, obj=None):
        return False

    @staticmethod
    def image(obj: Photo):
        return format_html('<img height="50" src="https://minicup.tatranlitovel.cz/media/thumb/{}"/>', obj.filename)
