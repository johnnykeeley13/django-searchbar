if __debug__:
    from django.http import HttpRequest

import collections
from django_searchbar.forms import SearchBarForm
from django.middleware import csrf
from django.utils.safestring import mark_safe
from django.db.models import Q


def listify(item):
    """
    A simple function to create a list if item is not a list or a tuple
    @type item: str|iterable
    @return list
    """

    if not isinstance(item, (list, tuple)):
        item = [item]
    return item


class SearchBar:

    """
    Usage:
        In your view, do this:
        def my_view(request):
            search_bar = SearchBar(request, ['name', 'age'])
            if search_bar.is_valid():
                name_value = search_bar['name']
    """

    def __init__(self, request, fields=None, replacements={}, method='post'):

        assert isinstance(request, HttpRequest), 'request should be an instance of the HttpRequest object'
        assert isinstance(fields, (type(None), list, tuple, str, dict)), 'fields should be None, list or a tuple containing strings'
        assert isinstance(replacements, (dict, collections.Callable)), 'fields should be None, list or a tuple containing strings'

        if __debug__ and isinstance(fields, (list, tuple)):
            for item in fields:
                assert isinstance(item, (str, dict)), '%s should be a string or a dictionary containing label' % item

        if fields:
            fields = listify(fields)

            self.form = SearchBarForm(request.GET or request.POST, fields=fields)

        self.request = request
        self.replacements = replacements
        self.fields = fields
        self.action = ''
        self.method = method.lower().strip()

    def is_valid(self, *args, **kwargs):
        """
        Validates the SearchBar instance.
        All required argument you pass here, should end up in request results to pass.
        @return bool
        """

        def check_validation(self, item):
            if isinstance(item, dict):
                if item.get('required', False) and self.form.cleaned_data.get(item['label'], '') == '':
                    return False
            elif isinstance(item, str):
                if self.form.cleaned_data.get(item, '') == '':
                    return False

            return True

        if not self.fields:
            return False

        form_validation = self.form.is_valid()

        if form_validation and args:
            args = listify(args)
            form_validation = all(self.form.cleaned_data.get(item, '') != '' for item in args)

        elif form_validation and self.fields:
            for item in self.fields:
                if not check_validation(self, item):
                    form_validation = False
                    break

        return form_validation

    def as_form(self):
        csrf_ = ''
        if self.method == 'post':
            csrf_ = "<input type='hidden' name='csrfmiddlewaretoken' value='{0}' />".format(csrf.get_token(self.request))
        submit_button = '<input type="submit" value="submit" />'
        return_string = "<form method='%s' action='%s'>%s %s %s</form>" % (self.method, self.action, csrf_, self, submit_button)
        return mark_safe(return_string)

    def get_filters(self, *args, lookup_string=''):
        """
        Returns a Q object based on all the input from query term
        @param lookup_string: adds this ``lookup_string`` to query lookup of all fields
        @param args: if provided, items you need to be in queryset. otherwise it's everything
        """
        filters = Q()
        lookup_string = lookup_string.lower().strip()

        if args:
            __fields = [k for k in self.fields if k in args]
        else:
            __fields = self.fields

        for field in __fields:
            if isinstance(field, dict):
                field = field['label']
            if self[field]:
                replacement = self.replacements.get(field, field)
                if isinstance(replacement, collections.Callable):
                    replacement = replacement(field)

                if lookup_string:
                    field_name = "{field}__{method}".format(field=replacement, method=lookup_string)
                else:
                    field_name = replacement

                filters &= Q(**{field_name: self[field]})
        return filters

    def __getitem__(self, index):
        if index == 'as_form':
            return self.as_form()

        return self.form.cleaned_data.get(index, '')

    def __str__(self):
        return str(self.form)
