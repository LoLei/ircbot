import os
from pathlib import Path

import yaml


CONFIG = dict()

settings_path = os.path.dirname(os.path.abspath(__file__))
config_path = Path(settings_path) / "config.yaml"

with open(str(config_path), 'r') as stream:
    try:
        CONFIG = yaml.safe_load(stream)
    except yaml.YAMLError as e:
        print(e)
