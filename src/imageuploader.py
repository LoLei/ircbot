from typing import Dict

from imgurpython import ImgurClient

from src.settings import CONFIG

CLIENT = ImgurClient(
    CONFIG['imgur_client_id'],
    CONFIG['imgur_client_secret']
    )


def upload(path: str) -> Dict:
    return CLIENT.upload_from_path(path, config=None, anon=True)
