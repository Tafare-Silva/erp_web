from django import template

from ..columns import format_value

register = template.Library()


@register.filter
def get_item(mapping, key):
    if hasattr(mapping, "get"):
        return mapping.get(key, "")
    return getattr(mapping, key, "")


@register.filter
def formato(value, kind):
    return format_value(value, kind)
