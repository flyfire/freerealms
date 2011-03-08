class Component(object):

    pass


class CounterComponent(Component):

    counter = Property("counter", int, list=True)

    
