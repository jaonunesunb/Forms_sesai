from arangodb_client import _key, aql_subclasses

def db_get_subclasses(class_uri: str):
    class_key = _key(class_uri)
    return aql_subclasses(class_key)
