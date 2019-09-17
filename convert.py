# -*- coding: utf-8 -*-
import inspect
import uuid
import datetime as dt
import decimal
from flask_restplus import fields, Model
from sqlalchemy.dialects import postgresql, mysql, mssql
import sqlalchemy as sa

from .exceptions import ModelConversionError
from .fields import Enum, UUID

def _is_field(value):
    return isinstance(value, type) and issubclass(value, fields.Raw)

from sqlalchemy.orm import class_mapper
from sqlalchemy.orm.properties import ColumnProperty
from sqlalchemy.orm.relationships import RelationshipProperty
import collections

def multi_getattr(obj, attr: str, default = None):
    """
    Get a named attribute from an object; multi_getattr(x, 'a.b.c.d') is
    equivalent to x.a.b.c.d. When a default argument is given, it is
    returned when any attribute in the chain doesn't exist; without
    it, an exception is raised when a missing attribute is encountered.

    """
    attributes = attr.split(".")
    for i in attributes:
        try:
            obj = getattr(obj, i)
        except AttributeError:
            return default
    return obj


def getitem_by_index(obj, attr: str, default=None):
    '''
    returns an attribute by index.
    '''
    attributes = attr.split(".")
    for i in attributes:
        try:
            if i.endswith(']'):
                temp = i.split('[')
                i = ''.join(temp[0])
                index = int(temp[1].strip(']'))
                if i:
                    obj = getattr(obj, i)
                obj = obj[index]
            else:
                obj = getattr(obj, i)
        except (AttributeError, IndexError):
            return default
    return obj

def prop_2_lambda(propname: str, default=None):
    '''
    helper function
    Creates a lambda expression that has the propname and default value already specified
    for the multi_getattr function. self is provided for compatibility with FIELD_MAPPING
    '''
    return lambda self, prop: multi_getattr(prop, propname, default)

# name to append to end of the auto generated models of relationship properties
MODEL_POSTFIX = "Model"

class SQLAlchemyModelConverter():
    # maps python types to restplus types
    PYTHON_TYPE_MAPPING = {
        str: fields.String,
        bytes: fields.String,
        dt.datetime: fields.DateTime,
        float: fields.Float,
        bool: fields.Boolean,
        tuple: fields.Raw,
        list: fields.List,
        set: fields.Raw,
        int: fields.Integer,
        uuid.UUID: UUID,
        dt.time: fields.DateTime,
        dt.date: fields.DateTime,
        decimal.Decimal: fields.Decimal,
    }

    # sets the default mapping for kwargs on restplus fields to a lambda function to get the value for kwargs from a column or relationship
    DEFAULT_FIELD_MAPPING = {
        "required" :  lambda self, prop: not getattr(prop, "nullable", True),
        "description" : prop_2_lambda("description"),
        #"default" : prop_2_lambda("default"),
    }

    """
    maps a restplus field to dictionary where the value is a lambda function to get the value for kwargs from a column or relationship
    the key is the kwargs key
    the lookup is: Field.Class -> dict { "constructor_arg_name" : (lambda(SQLAlchemyModelConverter, SqlAlchemy_Object_property) -> value_for_arg ) } 
    """
    FIELD_MAPPING = {
        fields.String: {
            "max_length" : prop_2_lambda("length"),
        },
        fields.DateTime: {},
        fields.Float: {},
        fields.Boolean: {},
        fields.Raw: {},
        fields.List: {
            "cls_or_instance" : lambda self, prop: self._get_field_class_for_data_type(multi_getattr(prop, "type.item_type")) or fields.Raw,
            "max_items" : prop_2_lambda("length"), 
            "unique" : prop_2_lambda("unique"),
        },
        fields.Integer: {},
        UUID: { 
            "max_length" : prop_2_lambda("length"),
        },
        fields.Decimal: { 
            "max_length" : prop_2_lambda("length"),
        },
        Enum: { 
            "max_length" : prop_2_lambda("length"),
            "enum" : prop_2_lambda("type.enums"),
        },
        fields.Nested: {
            "required" : None,
            "model" : lambda self, prop: Model(prop.mapper.class_.__name__ + MODEL_POSTFIX, {}),#self._get_field_class_for_data_type(getitem_by_index(list(getattr(prop, "local_columns", set())), "[0].type")) or fields.Raw,
            "allow_null" : lambda self, prop: getitem_by_index(list(getattr(prop, "local_columns", set())), "[0].nullable"),
            #"skip_none" : lambda self, prop: None,
            "as_list" : prop_2_lambda("uselist"),
        },
    }

    # maps the SQLA type to a restplus field
    # SQLA field class -> restplus field class
    SQLA_TYPE_MAPPING = {
        sa.Enum: Enum,
        postgresql.BIT: fields.Integer,
        postgresql.UUID: UUID,
        postgresql.MACADDR: fields.String,
        postgresql.INET: fields.String,
        postgresql.JSON: fields.Raw,
        postgresql.JSONB: fields.Raw,
        postgresql.HSTORE: fields.Raw,
        sa.ARRAY: fields.List,
        mysql.BIT: fields.Integer,
        mysql.YEAR: fields.Integer,
        mysql.SET: fields.List,
        mysql.ENUM: Enum,
        mssql.BIT: fields.Integer,
        sa.sql.sqltypes.NullType: fields.Raw,
    }

    if hasattr(sa, "JSON"):
        SQLA_TYPE_MAPPING[sa.JSON] = fields.Raw
    if hasattr(postgresql, "MONEY"):
        SQLA_TYPE_MAPPING[postgresql.MONEY] = fields.Arbitrary

    
    def fields_for_model(
        self,
        model,
        only=None,
        exclude=None,
        declared_fields=None,
        dict_cls=dict,
        include_relationships: bool = False
    ) -> dict:
        result = dict_cls()
        declared_fields = declared_fields or {}
        for prop in self.get_property_iterator(model, only, exclude, include_relationships):
            field = declared_fields.get(prop.key) or self.sql_property2field(prop)
            if field:
                result[prop.key] = field
        return result

    def get_property_iterator(self, class_, only, exclude, include_relationships):
        """
        Iterates through the properties of SQLalchemy class
        :param class_: sqlalchemy class
        :param only: only include specified fields
        :param exclude: exclude specified fields
        :param include_relationships: include relationship properties
        """
        for prop in class_mapper(class_).iterate_properties:
            if self._should_exclude_field(prop, only=only, exclude=exclude, include_relationships=include_relationships):
                continue
            yield prop

    def _should_exclude_field(self, prop, only=None, exclude=None, include_relationships=False) -> bool:
        """
        Checks if specified field should be excluded from the model.
        automatically excludes all fields that start with '_'
        :param prop: property to check
        :param only: only include specified fields
        :param exclude: exclude specified fields
        :param include_relationships: include relationship properties
        :returns: bool
        """
        name = prop.key
        if name.startswith("_"):
            return True
        if only and name not in only:
            return True
        if exclude and name in exclude:
            return True
        if not include_relationships and type(prop) is RelationshipProperty:
            return True
        return False

    def sql_property2field(self, prop) -> fields.Raw:
        """
        maps a sql alchemy property to a restplus field, gets the kwargs, and returns an instance of
        restplus field.
        """
        field_instance = None
        proptype = type(prop)

        if proptype is ColumnProperty:
            column = prop.columns[0]
            field_class = self.get_field_class_for_column(column)
            if not field_class:
                return None

            field_kwargs = self.get_field_kwargs_for_column(field_class, column)
            field_instance = field_class(**field_kwargs)
            
        elif proptype is RelationshipProperty:
            field_class = self.get_field_class_for_relationship(prop)
            if not field_class:
                return None
            field_kwargs = self.get_field_kwargs_for_relationship(field_class, prop)
            field_instance = field_class(**field_kwargs)
        return field_instance

    def get_field_class_for_column(self, column: ColumnProperty):
        '''
        Gets the restplus field class type for a sqlalchemy column
        '''
        return self._get_field_class_for_data_type(column.type)

    def get_field_kwargs_for_column(self, field_class: fields.Raw, column: ColumnProperty) -> dict:
        '''
        Gets the kwargs used for initializing a specified column. Looks up the values
        through DEFAULT_FIELD_MAPPING + FIELD_MAPPING, then gets the value for the field
        by calling the lambda expression specified.
        '''
        field_kwargs = {}
        field_map = self.DEFAULT_FIELD_MAPPING.copy()
        field_map.update(self.FIELD_MAPPING[field_class])

        for (field_name, field_value) in field_map.items():
            arg_value = field_value(self, column)
            if arg_value is not None:
                field_kwargs[field_name] = arg_value

        return field_kwargs


    def get_field_class_for_relationship(self, relationship: RelationshipProperty):
        '''
        Returns the class type to be used for relationship properties
        '''
        return fields.Nested

    def get_field_kwargs_for_relationship(self, field_class: fields.Raw, relationship: RelationshipProperty) -> dict:
        '''
        Same as get_field_kwargs_for_column
        Gets the kwargs used for initializing a specified column. Looks up the values
        through DEFAULT_FIELD_MAPPING + FIELD_MAPPING, then gets the value for the field
        by calling the lambda expression specified.
        returns a dict of field name: value pairs for use with kwargs
        '''
        field_kwargs = {}
        field_map = self.DEFAULT_FIELD_MAPPING.copy()
        field_map.update(self.FIELD_MAPPING[field_class])

        for (field_name, field_value) in field_map.items():
            if field_value is not None:
                arg_value = field_value(self, relationship)
                if arg_value is not None:
                    field_kwargs[field_name] = arg_value

        return field_kwargs

    def _get_field_class_for_data_type(self, data_type):
        '''
        Gets the restplus field class for the specified data type
        uses SQLA_TYPE_MAPPING to lookup the target type for the field
        '''
        field_cls = None
        types = inspect.getmro(type(data_type))
        # First search for a field class from self.SQLA_TYPE_MAPPING
        for col_type in types:
            if col_type in self.SQLA_TYPE_MAPPING:
                field_cls = self.SQLA_TYPE_MAPPING[col_type]
                break
        else:
            # Try to find a field class based on the column's python_type
            try:
                python_type = data_type.python_type
            except NotImplementedError:
                python_type = None

            if python_type in self.PYTHON_TYPE_MAPPING:
                field_cls = self.PYTHON_TYPE_MAPPING[python_type]
            else:
                if hasattr(data_type, "impl"):
                    return self._get_field_class_for_data_type(data_type.impl)
                raise ModelConversionError(
                    "Could not find field column of type {}.".format(types[0])
                )
        return field_cls
