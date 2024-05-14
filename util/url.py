class Url:
    def __init__(self, url: str):
        self.url = url
        self.https = False if url.startswith("http://") else True
        self.endpoint = self._endpoint()

    def _endpoint(self):
        if self.https:
            url = self.url.replace("https://", "")

        else:
            url = self.url.replace("http://", "")

        splitted = url.split("/")
        return url.replace(splitted[0], "", 1)