from flask_restplus import Api
from flask_sqlalchemy import SQLAlchemy
from .schema import SQLAlchemyToRestPlus

db = SQLAlchemy(session_options={'autocommit': False, 'autoflush': True})
Base = db.Model

class Users(Base):
    __tablename__ = 'Users'

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    login = db.Column(db.Integer, nullable=False)

class Computers(Base):
    __tablename__ = 'Computers'

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(50), unique=True, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    user = db.relationship("Users", lazy='joined')

    hostname = db.Column(db.String(100), nullable=True, unique=True)
    ip_address = db.Column(db.String(30), nullable=True)


"""
Create a User model and add it to the API models
"""
Users_Model_Instance = SQLAlchemyToRestPlus("UsersModel", {}, model=Users)
api.add_model("UsersModel", Users_Model_Instance)


"""
Create a computer model, including relationships
this will automatically turn the user relationship into a nested field looking for a model named UsersModel
"""
Computer_Model_Instance = SQLAlchemyToRestPlus("ComputerModel", {}, model=ComputerModel, include_relationships=True )
api.add_model("ComputerModel", Computer_Model_Instance)


"""
Create a computer model, excluding user_id
"""
Computer_Model_Instance_without_user_id = SQLAlchemyToRestPlus("ComputerWithoutUserIDModel", {}, model=ComputerModel, exclude=['user_id',] )
api.add_model("ComputerWithoutUserIDModel", Computer_Model_Instance_without_user_id)


"""
Create a User model with additional propertie phone_number defined
"""
Users_WithPhone_Model_Instance = SQLAlchemyToRestPlus("UsersWithPhoneModel", {
    'phone_number': fields.String,
}, model=Users)
api.add_model("UsersWithPhoneModel", Users_Model_Instance)


"""
Create a User model overwriting login column
"""
Users_WithPhone_Model_Instance = SQLAlchemyToRestPlus("UsersStringLoginModel", {
    'login': fields.String,
}, model=Users)
api.add_model("UsersStringLoginModel", Users_Model_Instance)

"""
Create a User model with only id and first_name
"""
Users_Model_Instance = SQLAlchemyToRestPlus("UsersFirstNameModel", {}, model=Users, only=['id', 'first_name'])
api.add_model("UsersFirstNameModel", Users_Model_Instance)