# pybrightsign
BrightSign APIs for humans.  Python module to simplify using the BrightSign BSN/BSNEE [REST API](https://docs.brightsign.biz/display/DOC/REST+API).

> NOTE: Now in Beta.  Pretty stable, but still subject to breaking changes in later releases.

Install with `pip` as usual:

`pip install pybrightsign`

## Introduction

This library handles many of the fussy details when using BrightSign APIs (esp. the Upload API), freeing the developer from much boilerplate code.

* construct a `Server` object
* authorize it
* use its `requests` object - as you would the plain-jane requests object but simpler
* use its handy utility methods

Here is a full example, using the [Devices endpoint](https://docs.brightsign.biz/display/DOC/Devices+Endpoints) to show a list the names of all devices in a network:

```python
from pybrightsign import Server

creds = {
    'network': 'Demo',
    'username': 'user@example.com',
    'password': 'swordfish'
}

# First create a server object using the domain name of your BSNEE instance
bsnee = Server('brightsign.example.com')
bsnee.authorize(creds)

# Now use the server's requests object as you would normally, 
# without worrying about api version, tokens, url prefix, basic headers, etc.
response = bsnee.requests.get('/devices')
response.raise_for_status()

devices = response.json()['items']

for device in devices:
    print(device['name'])
```

If you have ever wrestled with the [Upload endpoint](https://docs.brightsign.biz/display/DOC/Upload+Endpoints), you will love how easy it now is to upload stuff.  Here is a full example that uploads a video, an image (to a particular folder), then a web site (including the index.html and all css, js, images, etc. in the same folder):

```python
from pybrightsign import Server

creds = {
    'network': 'Demo',
    'username': 'user@example.com',
    'password': 'swordfish'
}

bsnee = Server('brightsign.example.com')
bsnee.authorize(creds)

bsnee.upload_file('promo.mp4')
bsnee.upload_file('logo.png', r'\Shared\Images')
bsnee.upload_web_folder('./website/index.html')
```

## Methods

This section will cover the following methods:

* the `Server` class's constructor
* `authorize(creds)`
* `requests` (not a method, but it's covered here)
  * prior knowledge of the [requests](https://docs.python-requests.org/en/master/) module is pretty much required
  * you should also be aware of the [BrightSign's REST API and its endpoints](https://docs.brightsign.biz/display/DOC/REST+API)
  * you do not need to worry about the [Upload endpoints](https://docs.brightsign.biz/display/DOC/Upload+Endpoints), as they are completely wrapped by the upload utility methods
* `get_network_names()`
* `switch_network(network_name)`
* `move_device_to_group(device_id, new_group_id)`
* Upload utility methods
  * `upload_file(filepath, [to_folder])`
  * `upload_web_folder(site_name, index_path)`

### Constructor

To construct a `Server` object you need a valid domain name of the BSN/BSN.Cloud instance.  The following constructor examples all begin with:

```python
from pybrightsign import Server
domain = 'brightsign.example.com'
```

> NOTE:  If you are following along, please replace `brightsign.example.com` with your domain name or these examples will fail.

#### Minimal

The most basic construction uses only the domain name - which is required.

```python
server = Server(domain)
```

This assumes the API subdomain is `api` and all calls to the API will begin with 'https://api.brightsign.example.com'.  You can confirm this (and the API version) like this, for example:

```python
>>> print(server)
https://api.brightsign.example.com/2019/03/REST
```



#### API Subdomain

If your API is located in a different subdomain than `api`, you can specify it like this

```python
server = Server(domain, api_subdomain='apitest')
```

Now all API calls will begin with 'https://apitest.brightsign.example.com'



#### API Version

Although optional, if you know the API version you should specify it.  If you do not the constructing a `Server` object prints the following warning:

```
WARNING: api_version (None) is invalid for https://api.brightsign.cri.com.  Attempting to discover correct api_version. This may take several seconds. To remove this warning (and this delay), please supply a valid api_version.
```

API versions are in the form of `YYYY/MM` .  The constructor tries to discover the API version by first checking the known versions (from most recent to oldest).  If a valid version is not found, it then tries the current year and current month, and keeps trying the previous month until it either finds a valid version or reaches the oldest known version (no point trying beyond that).  This is handy if you do not know the version, but clearly this takes time that can be avoided if you tell it the version.

```python
server = server(domain, api_version='2019/03')
```



### Authorize

Once you have constructed a `Server` object (using any of the means above), you must authorize it before making calls.  Create a dictionary with your credentials and pass it to the `authorize()` method.

```python
creds = {
    'network': 'Demo',
    'username': 'user@example.org',
    'password': 'swordfish'
}
server.authorize(creds)
```

You can use the server object to see where you are connected any with which user:

```python
>>> print(server)
https://api.brightsign.example.com/2019/03/REST as Demo/user@example.org
```



### Requests

Once authorized, you can now use the server's `requests` object.  Use this exactly as you would a regular [requests](https://docs.python-requests.org/en/master/) object except

* you don't have to manage the auth token, nor create a headers dict with the token.
* you don't have to use a full URL - only the endpoint path.  For example, instead of using `https://api.brightsign.example.com/2019/03/REST/contents` you can simply use `/contents`
* Default headers
  * By default all request have `Accept: application/json` in the headers, 
  * In the case of POST, PUT, or PATCH will also have `Content-type: application/json`
  * If you need different Accept or Content-type headers - or if you need additional headers, pass a headers dict as you normally would.  It will get merged into the managed headers (i.e. the one that has the token)

Examples will make all of this clearer:

Let's say you want to POST a presentation.  Using only `requests` you would do something like this (assuming you had created the `get_presentation()` and `get_token()` methods)

```python
token = get_token()
presentation = get_presentation()  # returns a JSON string of the presentation to POST
headers = {
    'Accept':  'application/json',
    'Content-type': 'application/json',
    'Authentication': f'Bearer {token}'
}
response = requests.post('https://api.brightsign.example.com/2019/03/REST/presentations', data=presentation, headers=headers)
```

With `pybrightsign` you don't need `get_tokens()`, and your code would look like this (after the `server` object was authorized):

```python
presentation = get_presentation()
server.requests.post('/presentations', data=presentation)
```

If you wanted a list of devices in XML insetead of JSON, you can override the `Accept:` header like this:

```python
reponse = server.get('/devices', headers={'Accept': 'application/xml'})
```

You can stop reading here and you will have the full power of BrightSign APIs as your disposal.  There are some utility methods which make some routine tasks a bit simpler.  Each of these can be done with just the server's requests, but why would you?



### List Networks

To see which networks you have access to you could use `server.requests.get('/self/networks')`, iterate through the response json `items` array and pull out the `name` field of each object.  Or use `get_network_names()`

```python
>>> server.get_network_names()
['admin', 'Demo', 'OtherNetwork']
```



### Switch Networks

If you are authorized on one network, you can easily switch to a different network without having to re-authorize:

```python
>>> server.switch_network('OtherNetwork')
>>> print(server)
https://api.brightsign.example.com/2019/03/REST as NewNetwork/user@example.org
```



### Move a device

To move a device from one group to another:

```python
server.move_device_to_group(device_id, new_group_id)
```

`device_id` can be the device's ID number, or its serial number

`new_group_id` can be the group's ID number or its name.

### Upload a file or a Website

To upload a file, you could wrestle with the [Upload endpoint](https://docs.brightsign.biz/display/DOC/Upload+Endpoints), or just use `upload_file()`

```python
server.upload_file('./img/logo.png')
```

You can optionally specify which folder (virtualPath) to upload to:

```python
server.upload_file('./img/logo.png', '\\Shared\\Images')
```

Backslashes in the virtualPath must be escaped with backslashes.  Or use python's `r-string` notation (raw string)

```python
server.upload_file('./img/logo.png', r'\Shared\Images')
```

Similarly, to upload a Website, point to the path/name of the site's index file.  This will upload the index file and all other files in the same folder and its subfolders:

For example, if your website is a set of files like this:

```
./my-site
|   index.html
|
|--css
|       style.css
|
|--img
|       background.jpg
|       logo.png
|
|--js
    |--app
    |     ui.js
    |  
    |--utils
          api.js
          tools.js
```

You upload this folder with the name 'MySite' (for example) like this:

```python
server.upload_web_folder('MySite', './my-site/index.html')
```

Replace `index.html` with the actual site's entry page is (e.g. `default.htm` )
