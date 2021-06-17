import requests

def urljoin(base, path):
    return '{0}/{1}'.format(base.rstrip('/'), path.lstrip('/'))
    

class SessionWithUrlBase(requests.Session):
    def __init__(self, url_base=None, token=None, *args, **kwargs):
        super(SessionWithUrlBase, self).__init__(*args, **kwargs)
        self.url_base = url_base
        self.token = token

    def request(self, method, url, **kwargs):
        modified_url = urljoin(self.url_base, url)

        if 'headers' in kwargs:
            if 'Accept' not in kwargs['headers']:
                kwargs['headers']['Accept'] = 'application/json'
        else:
            kwargs['headers'] = {'Accept': 'application/json'}

        return super(SessionWithUrlBase, self).request(method, modified_url, **kwargs)

requests.Session = SessionWithUrlBase
