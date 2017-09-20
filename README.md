
# eye_rest API Framework

## Overview

SAFRS_rest purpose is to create a self-documenting API for the sqlalchemy database objects and relationships. These objects can be serialized to JSON and can be created, deleted and updated through the REST API. class and method description and examples are parsed and shown in the swagger web interface.

The eye_rest directory contains the code to construct documented REST APIs
It consists of 
- db.py : sqlalchemy database definitions 
- restful.py : REST web bindings
- swagger_doc.py : API documentation, implemented as decorators
- demo.py : a small sample application 
- demo_relationship.py : an extension of the demo.py to demonstrate relationship functionality

## HTTP Methods

The objects can be queried using a REST API. The APIs support following HTTP operations:

- GET : Retrieve an object or a list of object identifiers
- PUT : Create or Update an object. The "Location" header of the response contains the URL of the resource
- DELETE: Delete an object
- POST : Apply a method to an object (e.g. user.send_mail(email) instructs the backend to send an email)

## Objects

Database objects are implemented as subclasses of the SAFRSBase and SQLAlchemy model classes. The SQLAlchemy columns are serialized to JSON when the corresponding REST API is invoked. 

code from demo.py illustrates how the API is built and documented:

```python
class User(SAFRSBase, db.Model):
    '''
        description: User description
    '''
    __tablename__ = 'users'
    id = Column(String, primary_key=True)
    name = Column(String, default = '')
    email = Column(String, default = '')

    # Following method is exposed through the REST API 
    # This means it can be invoked with a HTTP POST
    @documented_api_method
    def send_mail(self, email):
        '''
            description : Send an email
            args:
                email:
                    type : string 
                    example : test email
        '''
        content = 'Mail to {} : {}\n'.format(self.name, email)
        return { 'result' : 'sent {}'.format(content)}

```

The User class is implemented as a subclass of 
- db.Model: SQLAlchemy object
- SAFRSBase: Implements JSON serialization for the object and generates (swagger) API documentation

This User object is then exposed through the web interface using the Api object

```python 
api.expose_object(User)
``` 

The User object REST methods are available on /User, the swagger schema is available on /api/swagger.json and the UI is available on /api/:
![User Swagger](images/USER_swagger.png)

## Methods

The ```send_mail``` method is documented with the ```documented_api_method``` decorator. 
This function generates a schema based on the function documentation. This documentation contains yaml specification of the API which is used by the swagger UI. 
This method can then be invoked with following HTTP POST Json payload:

![User Swagger](images/POST_swagger.png)

The yaml specification has to be in the first part of the function and class comments. These parts are delimited by four dashes ("----") . The rest of the comment may contain additional documentation.

## Relationships

Database object such as the User class from the demo.py example can be extended to include relationships with other objects. The demo_relationship.py contains following extension of the User clalss where a relationship with the Book class is implemented:

```python
class User(SAFRSBase, db.Model):
    '''
        description: User description
    '''
    __tablename__ = 'Users'
    id = Column(String, primary_key=True)
    name = Column(String, default = '')
    email = Column(String, default = '')
    books = db.relationship('Book', secondary = users_books_table)

...
``` 

A many-to-many database association table is defined which links users with books as follows:

```python
users_books_table = Table('users_books_table', db.Model.metadata,
    Column('user_id', String, ForeignKey('Users.id', onupdate="CASCADE")),
    Column('book_id', String, ForeignKey('Books.id', onupdate="CASCADE")),
    extend_existing=True
)
```

The Book class is simply another subclass of SAFRSBase and db.Model, similar to the previous User class:

```python
class Book(SAFRSBase, db.Model):
    '''
        description: Book description
    '''
    __tablename__ = 'Books'
    id = Column(String, primary_key=True)
    name = Column(String, default = '')
```

The User.book relationship can be queried in the API through the following endpoints:
![Relations Swagger](images/Relations_swagger.png)

- POST adds an item to the relationship
- DELETE removes an item from the relationship
- GET retrieves a list of item ids

The relationship REST API works similarly for one-to-many relationships. 

## Endpoint Naming
As can be seen in the swagger UI:
- the endpoint collection names are the SQLAlchemy __tablename__ properties (e.g. /Users )
- the parameter names are derived from the SAFRSBase class names (e.g. {UserId} )
- the the relationship names are the SAFRSbase class relationship names (e.g /books )

## HTTP Status Codes

HTTP status codes are used to signal success or failure of a REST operation: 
- 200 : OK 
- 201 : The request has been fulfilled and resulted in a new resource being created.
- 204 : No Content, DELETE operation was successful
- 400 : The services raised an exception, for example in case of invalid input
- 500 : Internal Server Error

In case of errors( status codes 400+ ), the log file contains a stacktrace.

## Implementation details
This section describes on a high level how eye_rest is implemented (for low level details you can check the code and comments)

### Variables for SQLAlchemy, Flask, MarshMallow, Logging

Some variables have to be globally (cross-module) defined:
- app : flask app
- db  : flask-sqlalchemy database instance
- ma  : sqlalchemy-marshmallow instance (used for serialization of database objects)
- log : python logging instances

### SAFRSBase

- \_\_new\_\_ 
- \_\_init\_\_
- get_list
- clone
- sample
- sample_id
- get_swagger_doc: generate swagger object model and POST method documentation.

### Api

The flask_restful_swagger_2 Api class has been extended with following methods:
- ```expose_object``` Create endpoints to access the SAFRSBase classes
- ```expose_relationship```

In addition to creating endpoints, these functions also apply the ```api_decorator``` decorators:
- implement cors
- generate swagger documentation
- wrap the implemented HTTP methods (get, post, put, etc. ) to commit to the database after a request and 
- implement exception handling

The standard Api ```add_resource``` method has been modified to parse the parameters generated by the SAFRSBase swagger methods

### SAFRSRestAPI 
SAFRSRestAPI is a superclass for dynamically generated flask-restful endpoints. 

### SAFRSRestRelationshipAPI

### Swagger Documentation

- ```swagger_doc```
- ```swagger_relationship_doc```

### Serialization

- MarshMallow
- ```eye_serialize``` 
- The restful ```SAFRSJSONEncoder``` class calls the SAFRSBase subclass to_dict method to convert object attributes to a python dictionary which is then converted to JSON.

## TODOs

GET on a collection should only return a list of object ids. Maybe use query params for dictionary items
