from docutils import core
from docutils.writers.html4css1 import Writer, HTMLTranslator

def reST_to_html(input_string):

    # See http://docutils.sourceforge.net/docutils/examples.py
    overrides = {'initial_header_level': 3, 'doctitle_xform': None}
    parts = core.publish_parts(
        source=input_string, writer_name='html', settings_overrides=overrides)
    return parts['fragment']

