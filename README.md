# flask_restplus_sqlalchemy
SQLAlchemy to flask_restplus model converter for python

This is a rather quick implementation of a converter that will convert SQLAlchemy models to Restplus models.

No support is provided whatsoever. Please see the examples.

To create a restplus model from a sqlalchemy model:

from flask_restplus_sqlalchemy import SQLAlchemyToRestPlus

myModel = SQLAlchemyToRestPlus("MyExampleModelModel", {}, model=MySqlAlchemyModelClass)
and add to the api:
api.add_model("MyExampleModelModel", myModel)

if you want to include relationships (please note that flask_restplus will throw an error if the relationship model is not included elsewhere. the relationship model name will be the relationship class + "Model"):
myModelWithRelationships = SQLAlchemyToRestPlus("MyExampleModelModelWithRelationships", {}, model=MySqlAlchemyModelClass, include_relationships=True)

to add additional fields not in the model:
from flask_restplus import fields
myModelWithExtraFields = SQLAlchemyToRestPlus("MyExampleModelModelWithExtraFields", {
    'my_additional_field': fields.String,
}, model=MySqlAlchemyModelClass)

to exclude fields:
myModelWithExcludedFields = SQLAlchemyToRestPlus("MyExampleModelModelWithExcludedFields", {}, model=MySqlAlchemyModelClass, exclude=['my_excluded_field',])
