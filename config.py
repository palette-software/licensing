import ConfigParser

# Setup Configuration
config = ConfigParser.ConfigParser()
config.read('licensing.ini')

def get_config(name):
    return config.get('config', name)

def get_config_int(name):
     return config.getint('config', name)

def get_config_bool(name):
     return config.getboolean('config', name)

def get_config_float(name):
     return config.getfloat('config', name)
