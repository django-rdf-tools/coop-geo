from django.template import Library, Node, TemplateSyntaxError

register = Library()

@register.filter
def varformat(val):
    return '_'.join(val.split('-'))
