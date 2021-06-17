# pybrightsign
Python module to simplify using the BrightSign BSN/BSNEE API.

> NOTE: this is early work in progress - interfaces subject to radical changes

Install with `pip` as usual:

`pip install pybrightsign`

## Introduction

This library abstracts away authorization details and Upload API details, leaving the developer free to use the APIs directly and at as low a level as one would if using just the requests library without a bunch of boilerplate code.

Here is an example of using the [Devices endpoint](https://docs.brightsign.biz/display/DOC/Devices+Endpoints) to show a list the names of all devices in a network:

```python
from pybrightsign import Server

creds = {
    'network': 'My BSN Network',
    'username': 'user@example.org',
    'password': 'swordfish'
}

bsnee = Server('brightsign.example.com')
bsnee.authorize(creds)

devices = bsnee.requests.get('/devices').json()['items']

for device in devices:
    print(device['name'])
```

Even more powerful is the abstraction of the [Upload endpoint](https://docs.brightsign.biz/display/DOC/Upload+Endpoints), for example uploading a video, an image (to a particular folder), then uploading a web site (including the index.html and all css, js, images, etc. in the same folder):

```python
from pybrightsign import Server

creds = {
    'network': 'My BSN Network',
    'username': 'user@example.org',
    'password': 'swordfish'
}

bsnee = Server('brightsign.example.com')
bsnee.authorize(creds)

bsnee.upload_file('promo.mp4')
bsnee.upload_file('logo.png', r'\Shared\Images')
bsnee.upload_web_folder('./website/index.html')
```

...more to come...

