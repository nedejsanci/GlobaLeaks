import os
from cyclone.util import ObjectDict as OD

class ConfigError(Exception):
    pass

def get_root_path():
    this_directory = os.path.dirname(__file__)
    root = os.path.join(this_directory, '..')
    root = os.path.abspath(root)
    return root

def get_install_path():
    return os.path.abspath(os.path.join(get_root_path(), '..'))

def get_glclient_path():
    path = '/tmp'

    # XXX move all these variables to a config file
    glclient_path = os.path.join(get_install_path(), 'GLClient', 'www')
    path = os.path.abspath(glclient_path)
    if not os.path.isdir(path):
        raise ConfigError("GLClient not found at the %s path" % glclient_path)

    return path

def get_db_file():
    root = get_root_path()
    db_dir = os.path.join(root, '_gldata')
    if not os.path.isdir(db_dir):
        os.mkdir(db_dir)
    db_file = os.path.join(db_dir, 'glbackend.db')
    return db_file

main = OD()
advanced = OD()

advanced.debug = True

main.glclient_path = get_glclient_path()

if advanced.debug:
    print "Serving GLClient from %s" % main.glclient_path

main.database_uri = 'sqlite:'+get_db_file()

advanced.db_thread_pool_size = 10
advanced.scheduler_thread_pool_size = 10

