# -*- coding: utf-8 -*-
from .convert import SQLAlchemyModelConverter
from flask_restplus import fields as rp_fields, Model, OrderedModel
import json
from collections import OrderedDict, MutableMapping
from abc import ABCMeta

def is_instance_or_subclass(val, class_):
    """Return True if ``val`` is either a subclass or instance of ``class_``."""
    try:
        return issubclass(val, class_)
    except TypeError:
        return isinstance(val, class_)

class SQLAlchemyToRestPlusMeta(ABCMeta):
    def __call__(cls, name, *args, **kwargs):
        """
        Meta class to create a model for restplus from a SQLAlchemy schema
        updates args with generated args from the model
        """
        model = kwargs.pop('model', None)
        if model is None:
            #model not supplied, use default
            return super(SQLAlchemyToRestPlusMeta, cls).__call__(name, *args, **kwargs)

        if args:
            fields = args[0]
        else:
            fields = kwargs.pop('fields', dict())
        only = kwargs.pop('only', None)
        exclude = kwargs.pop('exclude', None)
        model_converter = kwargs.pop('model_converter', SQLAlchemyModelConverter)
        include_relationships = kwargs.pop('include_relationships', False)
        sorted = kwargs.pop('sorted', True)
        
        if only and not isinstance(only, (list, set)):
            raise ValueError("`only` option must be a list or set.")
                 
        if exclude and not isinstance(exclude, (list, set)):
            raise ValueError("`exclude` option must be a list or set.")
            
        if only and exclude:
            raise ValueError(
                "Cannot set both `only` and `exclude` options"
                " for the same Schema."
            )

        dict_cls = dict
        declared_fields = SQLAlchemyToRestPlusMeta.get_declared_fields(fields)
        schema_fields = SQLAlchemyToRestPlusMeta.get_fields_from_sqlalchemy(model, model_converter, declared_fields=declared_fields, only=only, exclude=exclude, dict_cls=dict_cls, include_relationships=include_relationships)
        schema_fields.update(declared_fields)

        args = (schema_fields,) + args[1:] or None
        
        if sorted:
            instance = super(SQLAlchemyToRestPlusMeta, SortedSQLAlchemyToRestPlus).__call__(name, *args, **kwargs)
        else:
            instance = super(SQLAlchemyToRestPlusMeta, cls).__call__(name, *args, **kwargs)

        return instance
    

    @classmethod
    def get_declared_fields(cls, fields, field_class=rp_fields.Raw) -> dict:
        """
        gets the fields that are declared for the restplus model
        """
        if not isinstance(fields, (dict)):
            raise ValueError("`fields` option must be a dict.")

        declared_fields = {
            field_name:field_value
            for (field_name, field_value) in fields.items()
            if is_instance_or_subclass(field_value, field_class)
        }

        return declared_fields

    @classmethod
    def get_fields_from_sqlalchemy(cls,
        model,
        model_converter,
        declared_fields=None,
        only=None,
        exclude=None,
        dict_cls=dict,
        include_relationships=False,
        ) -> dict:
        """
        creates an instance of the converter and generates the fields for the model
        """

        if exclude is not None:
            exclude = set(exclude)

        converter = model_converter()

        model_fields = converter.fields_for_model(
            model,
            only=only,
            exclude=exclude,
            declared_fields=declared_fields,
            dict_cls=dict_cls,
            include_relationships=include_relationships,
        )
        return model_fields

class SQLAlchemyToRestPlus(Model, metaclass=SQLAlchemyToRestPlusMeta):
    '''
    A restplus model that utilizes a metaclass to generate the restplus model from a SQLAlchemy model
    :param fields: the first argument must be the extra fields to include in the model
    :param model: the SQLAlchemy model
    :param model_converter: the model converter to use (default SQLAlchemyModelConverter)
    :param only: only include specified fields
    :param exclude: exclude specified fields
    :param include_relationships: include relationship properties
    :param sorted: sort the model properties
    '''
    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        # do this to throw exception if model is broken
        json.dumps(self.__schema__)
        #print(jdump)

class SortedSQLAlchemyToRestPlus(SQLAlchemyToRestPlus):
    '''
    A model that sorts the properties

    :param str name: The model public name
    :param str mask: an optional default model mask
    '''
    @property
    def _schema(self):
        schema = super(SortedSQLAlchemyToRestPlus, self)._schema
        if 'properties' in schema:
            schema['properties'] = dict(sorted(schema['properties'].items()))
        return schema