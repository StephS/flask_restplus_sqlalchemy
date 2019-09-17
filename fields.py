# -*- coding: utf-8 -*-

from flask_restplus import fields

def get_primary_keys(model):
    """Get primary key properties for a SQLAlchemy model.

    :param model: SQLAlchemy model class
    """
    mapper = model.__mapper__
    return [mapper.get_property_by_column(column) for column in mapper.primary_key]

class Enum(fields.String):
    '''
    enum must be a list type
    '''
    pass

class UUID(fields.String):
    __schema_format__ = 'uuid'