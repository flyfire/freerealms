import urllib

from docutils.core import publish_parts    

from google.appengine.ext.webapp import template

from django.utils.safestring import mark_safe
from django.utils.encoding import smart_str, force_unicode

register = template.create_template_register()

# XXX: We don't need this if we implement an url instance method for the models.
@register.filter
def urlquote(value):
    return urllib.quote(value, '')

@register.filter
def restructuredtext(value):
    parts = publish_parts(source=smart_str(value), writer_name="html4css1",     
        settings_overrides={
            'initial_header_level': 3,
            'doctitle_xform': False,
            '_disable_config': True })
    return mark_safe(force_unicode(parts["fragment"]))
restructuredtext.is_safe = True

