from pssparser.model.field import Field
from pssparser.model.expr_id import ExprId
from pssparser.model.type_identifier import TypeIdentifier

class FieldComposite(Field):
    
    def __init__(self, 
                 name : ExprId,
                 tid : TypeIdentifier):
        super().__init__(name)
        self.tid = tid
        
    @property
    def children(self):
        return self.tid.target.children
    