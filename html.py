class WidgetClass(type):

    def render(cls, tb):
        pass

class Widget(object):
    __metaclass__ = WidgetClass

class ComplexPanelClass(WidgetClass):

    def render(cls, tb):
        pass

class ComplexPanel(Widget):
    __metaclass__ = ComplexPanelClass


class TestPanel(ComplexPanel):
    
    @
    
