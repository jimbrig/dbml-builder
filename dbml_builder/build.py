"""
gen.py - This script handles the generated model code. The two primary
         actions are (1) read in PyDBML and create the corresponding 
         Pydantic + SQLAlchemy code and (2) verify that the generated
         code matches the current DBML version and the generated file
         contents has not been changed.
"""

import sys
from hashlib import sha1
from json import dump, load
from pydbml import PyDBML
from omymodels import create_models
from os import makedirs, devnull
from os.path import exists, join
from pathlib import Path

from dbml_builder.fix import patch_ddl, patch_schema, patch_orm

INFO = 'info.json'
SCHEMAS = 'schema.py'
ORM = 'orm.py'


def get_dbml_version(dbml_path: str) -> str:
    """
    Read in the DBML file and retrieve the version
    """
    dbml = PyDBML(Path(dbml_path))
    return dbml.project.note.text
    

def verify(version: str, generated_dir: str) -> bool:
    """
    Check if the generated model code is still valid
    
    Verification has two checks:
      1. Ensure the version passed in matches the version used to 
         generate the model code.
      2. Check if the hash of contents of the generated files matches 
         from when they were initially generated.
    """
    info_path = join(generated_dir, INFO)
    schema_path = join(generated_dir, SCHEMAS)
    orm_path = join(generated_dir, ORM)
    if exists(info_path) and exists(schema_path):
        with open(orm_path, 'rb') as file:
            orm_hash = sha1(file.read()).hexdigest()
        with open(schema_path, 'rb') as file:
            schema_hash = sha1(file.read()).hexdigest()
        with open(info_path, 'r') as file:
            info = load(file)
        return info['version'] == version and info['schema_hash'] == schema_hash and info['orm_hash'] == orm_hash
    else:
        return False
 

def generate_models(dbml_path: str, generated_dir: str) -> None:
    """
    Generate model code from DBML

    Three files are generated:
      1. An info file which contains metadata used by the `verify` function.
      2. A file with Pydantic schemas corresponding to the contents of the DBML.
      2. A file with Sqlalchemy tables corresponding to the contents of the DBML.
    """
    makedirs(generated_dir, exist_ok=True)

    dbml = PyDBML(Path(dbml_path))
    ddl = patch_ddl(dbml.sql)

    # Even when passing silent flags, O! My Models prints to stdout
    visible = sys.stdout
    sys.stdout = open(devnull, 'w')

    schemas = create_models(ddl, models_type='pydantic', dump=False, exit_silent=True)
    schema_content = patch_schema(schemas['code'])
    schemas_handle = join(generated_dir, SCHEMAS)

    orm = create_models(ddl, models_type='sqlalchemy', dump=False, exit_silent=True)
    orm_content = patch_orm(orm['code'])
    orm_handle = join(generated_dir, ORM)

    sys.stdout = visible

    with open(schemas_handle, 'w') as file:
        file.write(schema_content)

    with open(orm_handle, 'w') as file:
        file.write(orm_content)


    info = {
      'version': get_dbml_version(dbml_path),
      'schema_hash': sha1(schema_content.encode()).hexdigest(),
      'orm_hash': sha1(orm_content.encode()).hexdigest()
    }

    with open(join(generated_dir, INFO), 'w') as file:
        dump(info, file) 



