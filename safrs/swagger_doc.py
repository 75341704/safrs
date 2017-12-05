#
# Functions for api documentation: these decorators generate the swagger schemas
#
import inspect, yaml, uuid, logging
from flask_restful_swagger_2 import Schema, swagger
from safrs.errors import ValidationError

log = logging.getLogger()

REST_DOC  = '__rest_doc' # swagger doc attribute name. If this attribute is set 
                        # this means that the function is reachable through HTTP POST

def parse_object_doc(object):
    api_doc  = {}
    obj_doc  = str(inspect.getdoc(object))    
    yaml_doc = None
    raw_doc  = obj_doc.split('----')[0]
    try:
        yaml_doc = yaml.load(raw_doc)
    except SyntaxError:
        pass                
        
    except Exception as e:
        raise ValidationError('Failed to parse api doc')    
    
    if isinstance(yaml_doc, dict):
        api_doc.update(yaml_doc)

    return api_doc


def documented_api_method(func):
    '''
        Decorator to expose functions in the REST API:
        When a method is decorated with documented_api_method, this means
        it becomes available for use through HTTP POST (i.e. public)
    '''
    api_doc = parse_object_doc(func)
    
    setattr(func, REST_DOC, api_doc)
    return func


def is_public(method):
    return hasattr(method, REST_DOC)

def get_doc(method):
    return getattr(method, REST_DOC, None)


def SchemaClassFactory(name, properties):
    '''
        Generate a Schema class, used to describe swagger schemas
    '''

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            # here, the properties variable is the one passed to the
            # ClassFactory call
            if key not in properties:
                raise ValidationError('Argument {} not valid for {}'.format( 
                                       (key, self.__class__.__name__) ))
            setattr(self, key, value)
    
    newclass = type( name, 
                     (Schema,),
                     {'__init__': __init__,
                      'properties' : properties
                    })
    
    return newclass


def schema_from_dict(name, schema_dict):

    result = {}
    for k, v in schema_dict.items():
        if type(k) == str:
            result[k] = { 'example' : v, 'type' : 'string' }
        if type(k) == int:
            result[k] = { 'example' : v, 'type' : 'integer' }
        if type(k) == dict:
            result[k] = { 'example' : schema_from_dict('{} sample'.format(k), v) }

    # generate random name 
    return SchemaClassFactory(name + str(uuid.uuid4()), result)

def swagger_doc(cls, tags = None):

    def swagger_doc_gen( func ):
        '''
            Decorator used to document (SAFRSBase) class methods exposed in the API
        '''
        default_id  = cls.sample_id()
        class_name  = cls.__name__ 
        table_name  = cls.__tablename__
        http_method = func.__name__.lower()
        parameters  = [{
                        'name': cls.object_id, # parameter id, e.g. UserId
                        'in': 'path',
                        'type': 'string',
                        'default': default_id,
                        'required' : True
                      }]

        if tags == None :
            doc_tags = [ table_name ]
        else:
            doc_tags = tags

        doc = { 'tags': doc_tags,
                'description': 'Returns a {}'.format(class_name),
              }

        responses = {}

        if http_method == 'get':
            doc['summary'] =  'Retrieve a {} object'.format(class_name)
            _ , responses = cls.get_swagger_doc(http_method)
            
        elif http_method == 'post':
            post_params, responses = cls.get_swagger_doc(http_method)
            doc['summary'] =  'Create a {} object'.format(class_name)

            for post_param in post_params:

                method_name = post_param['method']['name']
                method_desc = post_param['method']['description']
                model_name  = '{} {} {}'.format(http_method, class_name, method_name)
                param_model = SchemaClassFactory(model_name, post_param)
                continue
                parameters.append({
                                    'name': model_name,
                                    'in': 'body',
                                    'type': 'string',
                                    'description' : method_desc,
                                    'schema' : param_model,
                                    'required' : True
                                  })

            if post_params:
                post_model, responses = cls.get_swagger_doc('patch')
                print(class_name)
                sample = cls.sample()
                print(sample.to_dict())
                if sample:
                    sample_data = schema_from_dict('{} POST sample'.format(class_name) ,
                                                    { 'data' : 
                                                        { 'attributes' : sample.to_dict(), 
                                                          'id' : cls.sample_id(),
                                                          'type' : class_name 
                                                        }
                                                    })
                else:
                    sample_data = {}
                
                post_model = SchemaClassFactory('POST body {}'.format(class_name), {'data': sample_data })
                parameters.append({
                                    'name': 'POST body',
                                    'in': 'body',
                                    'description' : '{} attributes'.format(class_name),
                                    'schema' : sample_data,
                                    'required' : True
                                  })

        elif http_method == 'delete':
            doc['summary'] =  doc['description'] = 'Delete a {} object'.format(class_name)
            responses = { '204' : { 
                                    'description' : 'Object Deleted' 
                                    }
                        }

        elif http_method == 'patch':
            patch_model, responses = cls.get_swagger_doc(http_method)
            doc['summary'] =  'Update a {} object'.format(class_name)
            parameters.append({ 
                                'name': 'test',
                                'in': 'body',
                                'schema' : patch_model,
                                'description': '{} attributes'.format(class_name),
                                'required' : True
                              })
            responses = { '201' : { 
                                    'description' : 'Object Created' 
                                    }
                        }
        else:
            # one of 'options', 'head', 'patch'
            log.debug('no documentation for "{}" '.format(http_method))
        
        doc['parameters'] = parameters
        doc['responses']  = responses
        doc["produces"]   = [ "application/json" ]
        
        @swagger.doc(doc)
        def wrapper( self, *args, **kwargs ):
            val = func( self, *args, **kwargs )
            return val
        
        return wrapper

    return swagger_doc_gen


def swagger_relationship_doc(cls, tags = None):

    def swagger_doc_gen( func ):
        '''
            Decorator used to document relationship methods exposed in the API
        '''

        parent_class = cls.relationship.parent.class_
        child_class  = cls.relationship.mapper.class_
        class_name   = cls.__name__ 
        table_name   = cls.__tablename__
        http_method  = func.__name__.lower()
        parameters   = [{
                        'name': parent_class.object_id,
                        'in': 'path',
                        'type': 'string',
                        'default': parent_class.sample_id(),
                        'description': '{} item'.format(parent_class.__name__),
                        'required' : True
                       },
                       {
                        'name': child_class.object_id,
                        'in': 'path',
                        'type': 'string',
                        'default': child_class.sample_id(),
                        'description': '{} item'.format(class_name),
                        'required' : True
                       }]

        parent_name = parent_class.__name__

        if tags == None :
            doc_tags = [ table_name ]
        else:
            doc_tags = tags

        doc = { 'tags': doc_tags,
                'description': 'Returns {} {} ids'.format(parent_name, cls.relationship.key),
              }

        responses = {}

        if http_method == 'get':
            doc['summary'] =  'Retrieve a {} object'.format(class_name)
            _ , responses = cls.get_swagger_doc(http_method)
            
        elif http_method == 'post':
            post_params, responses = cls.get_swagger_doc(http_method)
            doc['summary'] = 'Update {}'.format(cls.relationship.key)
            doc['description'] =  'Add a {} object to the {} relation on {}'.format(child_class.__name__, 
                                                                                cls.relationship.key,
                                                                                parent_name)
            # TODO: change this crap
            put_model, responses = child_class.get_swagger_doc('patch')
            
            for post_param in post_params:
                continue
                method_name = post_param['method']['name']
                method_desc = post_param['method']['description']
                model_name  = '{} {} {}'.format(http_method, class_name, method_name)
                param_model = SchemaClassFactory(model_name, post_param)
                parameters.append({
                                    'name': model_name,
                                    'in': 'body',
                                    'type': 'string',
                                    'description' : method_desc,
                                    'schema' : param_model,
                                  })

        elif http_method == 'delete':
            doc['summary'] = 'Delete from {} {}'.format(parent_name, cls.relationship.key)
            doc['description'] = 'Delete a {} object from the {} relation on {}'.format(child_class.__name__, 
                                                                                cls.relationship.key,
                                                                                parent_name)
            responses = { '204' : { 
                                    'description' : 'Object Deleted' 
                                    }
                        }

        elif http_method == 'patch' or http_method == 'put':
            put_model, responses = child_class.get_swagger_doc(http_method)
            doc['summary'] =  'Update a {} object'.format(class_name)
            parameters.append({ 
                                'name': 'test',
                                'in': 'body',
                                'type': 'string',
                                'schema' : put_model
                              })
            responses = { '201' : { 
                                    'description' : 'Object Created' 
                                    }
                        }
        else:
            # one of 'options', 'head', 'patch'
            log.debug('no documentation for "{}" '.format(http_method))
        
        doc['parameters'] = parameters
        doc['responses']  = responses
        
        @swagger.doc(doc)
        def wrapper( self, *args, **kwargs ):
            val = func( self, *args, **kwargs )
            return val
        
        return wrapper

    return swagger_doc_gen