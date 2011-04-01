from google.appengine.ext import db

class ComputedProperty(db.Property):
    data_type = None
    
    def __init__(self, derive_func, *args, **kwargs):
        """Constructor.
        
        Args:
          derive_func: A function that takes on argument, the model isntance,
                       and returns a calculated value.
        """
        super(ComputedProperty, self).__init__(*args, **kwargs)
        self.__derive_func = derive_func    
        
    def get_value_for_datastore(self, model_instance):
        return self.__derive_func(model_instance)


def generate_keywords(string):
    return (word.lower() for word in string.split())

