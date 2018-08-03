import sys
if sys.version_info[0] == 3:
    unicode = str
from safrs.errors import ValidationError
from sqlalchemy.types import PickleType, Text, String, Integer, DateTime, TypeDecorator, Integer, BLOB
import uuid, datetime, hashlib, re

try:
    from validate_email import validate_email
except:
    pass


STRIP_SPECIAL = '[^\w|%|:|/|-|_\-_\. ]'


class JSONType(PickleType):
    '''
        JSON DB type is used to store JSON objects in the database
    '''

    impl = BLOB

    def __init__(self, *args, **kwargs):        
        
        #kwargs['pickler'] = json
        super(JSONType, self).__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        
        if value is not None:
            value = json.dumps(value, ensure_ascii=True)
        return value

    def process_result_value(self, value, dialect):

        if value is not None:
            value = json.loads(value)
        return value


class SafeString(TypeDecorator):
    '''
        DB String Type class strips special chars when bound
    '''

    impl = String(767)

    def __init__(self, *args, **kwargs):

        super(SafeString, self).__init__(*args, **kwargs)     

    def process_bind_param(self, value, dialect):
        
        if value != None:
            result = re.sub(STRIP_SPECIAL, '_', value)
            if str(result) != str(value):
                #log.warning('({}) Replaced {} by {}'.format(self, value, result))
                pass
        else:
            result = value

        return result


class EmailType(TypeDecorator):
    '''
        DB Email Type class: validates email when bound
    '''

    impl = String(767)

    def __init__(self, *args, **kwargs):

        super(EmailType, self).__init__(*args, **kwargs)     

    def process_bind_param(self, value, dialect):
        if value and not validate_email(value):
            raise ValidationError('Email Validation Error {}'.format(value))

        return value

class UUIDType(TypeDecorator):

    impl = String(40)

    def __init__(self, *args, **kwargs):

        super(UUIDType, self).__init__(*args, **kwargs)     

    def process_bind_param(self, value, dialect):

        try:
            UUID(value, version=4)
        except:
            raise ValidationError('UUID Validation Error {}'.format(value))

        return value


class SAFRSID(object):
    '''
        - gen_id
        - validate_id
    '''
    primary_keys = ['id']
    delimiter = ','

    def __new__(cls, id = None):
        
        if id == None:
            return cls.gen_id()
        else:
            return cls.validate_id(id)

    @classmethod
    def gen_id(cls):
        return str(uuid.uuid4())

    @classmethod
    def validate_id(cls, id):
        for pk in id.split(cls.delimiter):
            try:
                uuid.UUID(pk, version=4)
                return pk
            except:
                raise ValidationError('Invalid ID')

    @property
    def name(self):
        return self.delimiter.join(self.primary_keys)

    @classmethod
    def get_id(self, obj):
        '''
            Retrieve the id string derived from the pks of obj
        '''
        values = [ getattr(obj,pk) for pk in self.primary_keys]
        return self.delimiter.join(values)

    @classmethod
    def get_pks(cls, id):
        '''
            Convert the id string to a pk dict
        '''
        values = id.split(cls.delimiter)
        result = dict(zip(cls.primary_keys, values))
        return result


def get_id_type(cls):
    primary_keys = [ col.name for col in cls.__table__.columns if col.primary_key ]
    id_type_class = type(cls.__name__ + '_ID' , (SAFRSID,), {'primary_keys' : primary_keys})
    return id_type_class


class SAFRSSHA256HashID(SAFRSID):

    @classmethod
    def gen_id(self):
        '''
            Create a hash based on the current time
            This is just an example 
            Not cryptographically secure and might cause collisions!
        '''
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f").encode('utf-8')
        return hashlib.sha256(now).hexdigest()

    @classmethod
    def validate_id(self, id):
        # todo
        pass

