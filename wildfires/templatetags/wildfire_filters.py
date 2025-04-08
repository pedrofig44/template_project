from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to access dictionary by key, similar to dict.get method.
    Returns None if the key doesn't exist.
    """
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def mult(value, arg):
    """
    Multiply the value by the argument
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
        
@register.filter
def percentage_of(value, total):
    """
    Calculate what percentage value is of total
    """
    try:
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0