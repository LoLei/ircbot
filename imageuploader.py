from imgurpython import ImgurClient


class ImageUploader():

    def __init__(self, client_id, client_secret):
        self.client_ = ImgurClient(client_id, client_secret)

    def upload(self, path):
        return self.client_.upload_from_path(path, config=None, anon=True)
