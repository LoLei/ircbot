from imgurpython import ImgurClient
# Own
from settings import CONFIG


CLIENT = ImgurClient(
    CONFIG['imgur_client_id'],
    CONFIG['imgur_client_secret']
    )


def upload(path):
    return CLIENT.upload_from_path(path, config=None, anon=True)
