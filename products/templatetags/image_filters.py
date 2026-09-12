from django import template

register = template.Library()

@register.filter(name='cld_optimize')
def cld_optimize(url):
    # only f_auto and q_auto - no resizes or crops -> original dimensions and framing are preserved
    if not url or '/upload/' not in url:
        return url
    return url.replace('/upload/', '/upload/f_auto,q_auto/', 1)
