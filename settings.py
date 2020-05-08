import yaml


CONFIG = dict()
with open("config.yaml", 'r') as stream:
    try:
        CONFIG = yaml.safe_load(stream)
    except yaml.YAMLError as e:
        print(e)
