import os
from pathlib import Path
import ntpath
from datetime import datetime
import json
import requests
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import LegacyApplicationClient as Client
from requests_oauthlib import OAuth2
import mimetypes
import hashlib
from . import sessionwithurlbase

# BrightSign API doc:   https://docs.brightsign.biz/display/DOC/BSN+API
# REST Upload API doc:  https://docs.brightsign.biz/display/DOC/Upload+Endpoints
#                       - note the steps for Webpages is different than individual files

UPLOAD_CHUNK_SIZE = 931072  # TODO: what is the best chunk size, and should it be settable in Server?
# UPLOAD_CHUNK_SIZE = 131072

KNOWN_API_VERSIONS = ['2019/03', '2017/01']

# TODO: move these methods, and possibly the static ones, to a utils module (incl. KNOWN_API_VERSIONS)?
# TODO: add logging, plus convert print() from upload_web_folder to logs
# TODO: factor out then recompose class for upload API
# TODO: robustify, esp. handling all cases after response = self.requests.xxx() (even if only logging)
# TODO: is AuthLib a better choice (e.g. auto refresh tokens) - https://docs.authlib.org/en/latest/client/oauth2.html#oauth2session-for-password

def _get_sha1(filename):
    h = hashlib.sha1()

    with open(filename, 'rb') as file:
        while True:
            chunk = file.read(h.block_size)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()

def _walk(path):
    for p in Path(path).iterdir():
        if p.is_dir():
            yield from _walk(p)
            continue
        yield p.resolve()

def _get_media_type(filename):
    try:
        media_type = mimetypes.guess_type(filename)[0].split('/')[0].title()  # TODO: robustify!!!
    except Exception:
        media_type = 'Auto'

    if media_type not in ['Auto', 'Text', 'Image', 'Video', 'Audio', 'Webpage', 'DeviceWebpage']:
        media_type = 'Auto'

    return media_type


def _update_token(token, refresh_token=None, access_token=None):
    if refresh_token:
        item = OAuth2Token.find(name=name, refresh_token=refresh_token)
    elif access_token:
        item = OAuth2Token.find(name=name, access_token=access_token)
    else:
        return

    # update old token
    item.access_token = token['access_token']
    item.refresh_token = token.get('refresh_token')
    item.expires_at = token['expires_at']
    item.save()


class Server:
    def __init__(self, server_domain, api_subdomain='api', api_version=None):
        self.base_url = f'https://{api_subdomain}.{server_domain}'
        self.username = ''
        if not self._test_api_version(api_version):
            print(f'WARNING: api_version ({api_version}) is invalid for {self.base_url}.  Attempting to discover correct api_version. This may take several seconds. To remove this warning (and this delay), please supply a valid api_version.')
            discovered_api_version = self._discover_version()
            if discovered_api_version:
                api_version = discovered_api_version
            else:
                raise ValueError(f'api_version ({api_version}) is invalid and no substitute was discovered.  Please specify a valid api_version for {self.base_url}.')

        self.api_version = api_version
        self.api_url = f'{self.base_url}/{api_version}/REST'
        self.upload_api_url = f'{self.base_url}/upload/{api_version}/REST'  # TODO: should this be validated?  (used to be /uploads)
        self.requests = requests.Session(url_base=self.api_url)
        self.upload_requests = requests.Session(url_base=self.upload_api_url)

    def authorize(self, creds=None):
        self._creds = creds

        kwargs = {**creds}
        del kwargs['username']
        del kwargs['password']
        del kwargs['network']

        self.username = f'{creds.get("network")}/{creds.get("username")}'
        password=creds.get('password')
        client_id = creds.get('client_id')
        oauth = OAuth2Session(client=Client(client_id)) #, update_token=_update_token)
        token = oauth.fetch_token(
            token_url=f'{self.api_url}/token',
            username=self.username,
            password=password,
            **kwargs
        )

        self.requests.auth = OAuth2(client_id, Client(client_id), token)
        self.upload_requests.auth = self.requests.auth

    def switch_network(self, network):
        # TODO: LOG: print(f'SWITCHING FROM {self.__str__()} TO {network}')
        self._creds['network'] = network
        self.authorize(self._creds)

    def upload_file(self, filepath, to_folder='\\'):
        filename = ntpath.basename(filepath)
        filesize = os.stat(filepath).st_size
        media_type = _get_media_type(filename)

        upload_job = {
            'fileName': filename,
            'fileSize': filesize,
            'mediaType': media_type,
            'fileLastModifiedDate': datetime.now().isoformat(),
            'virtualPath': to_folder,
            'sha1Hash': _get_sha1(filepath)
        }

        upload_start = self._start_file_upload_session(upload_job)
        upload_token = upload_start['upload_token']
        session = upload_start['upload_start'].json()
        session['virtualPath'] = to_folder

        content_id = None
        try:
            content_id = self._upload_file(filepath, session)
        except Exception as e:
            self._cancel_file_upload_session(upload_token)

        return content_id



    def upload_web_folder(self, site_name, index_path):
        # TODO: handle zip
        if self.upload_requests.auth is None:
            raise RuntimeError('Server object is not yet authorized')

        index_path = os.path.abspath(index_path)
        index_filename = os.path.basename(index_path)
        folder_name = os.path.dirname(index_path)

        root = Path(folder_name)

        if not os.path.exists(index_path):
            raise RuntimeError(f'{index_path} does not exist')

        index_file = None
        other_files = []

        for file in _walk(folder_name):
            if str(file) == index_path:
                index_file = file
            else:
                filename = ntpath.basename(file)
                other_files.append({
                    'fileName': filename,
                    'relativePath': ntpath.split(file.relative_to(root))[0] + '\\',
                    'fileSize': file.stat().st_size,
                    'mediaType': _get_media_type(filename),
                    'sha1Hash': _get_sha1(file),
                    'uploadPath': str(file)
                })

        web_upload_body = {
            'name': site_name,
            'filename': index_filename,
            'mediaType': 'Webpage',
            'fileSize': index_file.stat().st_size,
            'sha1Hash': _get_sha1(index_path),
            'assets': other_files
        }

        session = self._start_web_upload_session(web_upload_body)
        # TODO: assert session['state'] in ['Started']
        session['relativePath'] = '\\'

        try:
            self._upload_file(index_path, session)
            for asset in session['assets']:
                for other_file in other_files:
                    if other_file['sha1Hash'] == asset['shA1Hash']:  # note spelling discrepancy
                        asset['relativePath'] = other_file['relativePath']
                        self._upload_file(other_file['uploadPath'], asset)
                        break

            self._complete_web_upload_session(session)

        except Exception as e:
            self._cancel_web_upload_session(session['sessionToken'])

    def get_network_names(self):
        rtn = []
        if self.upload_requests.auth is None:
            raise RuntimeError('Server object is not yet authorized')

        response = self.requests.get('/self/networks')
        if response.ok:
            for network in response.json():
                rtn.append(network['name'])

        return rtn

    def move_device_to_group(self, device_id, new_group_id):
        # TODO: what if device already in group?
        # TODO: log more stuff
        response = self.requests.get(f'/devices/{device_id}')
        response.raise_for_status()
        device = response.json()

        response = self.requests.get(f'/groups/regular/{new_group_id}')
        response.raise_for_status()
        group = response.json()

        # TODO: LOG print(
        #     f'Moving device {device_id} from {device["targetGroup"]["name"]} ({device["targetGroup"]["id"]}) to {group["name"]} ({group["id"]})')

        device['targetGroup'] = {
            'id': group['id'],
            'name': group['name']
        }

        data = json.dumps(device)
        response = self.requests.put(f'/devices/{device_id}', data=data, headers=headers)
        # TODO: LOG print(response.status_code, response.reason, response.text)
        response.raise_for_status()


    def _test_api_version(self, api_version):
        if api_version:
            trial_url = f'{self.base_url}/{api_version}/REST/token'
            response = requests.get(trial_url)  # NOTE: not self.requests because we're not authorized yet
            if response.status_code >= 500:
                raise ValueError(f'{self.base_url} appears to be unavailable [{response.status_code} - {response.reason}]')
            return response.status_code == 400
        else:
            return False

    def _discover_version(self):
        for api_version in sorted(KNOWN_API_VERSIONS, reverse=True):
            if self._test_api_version(api_version):
                return api_version

        api_version = Server._next_version()
        keep_going = True
        while (True):
            if self._test_api_version(api_version):
                break

            api_version = Server._next_version(api_version)
            if api_version == '':
                break

        return api_version

    @staticmethod
    def _next_version(last_version=None):
        if last_version:
            a = last_version.split('/')
            year = int(a[0])
            month = int(a[1])
            month = 12 if month == 1 else month - 1
            if month == 12:
                year -= 1
        else:
            now = datetime.now()
            year = now.year
            month = now.month

        return f'{year}/{month:02}' if year >= 2017 else ''


    def _start_file_upload_session(self, upload_job):
        version = self.api_version.replace('/', '')
        headers = {
            'Accept': f'application/vnd.bsn.content.upload.status.{version}+json',
            'Content-type': f'application/vnd.bsn.start.content.upload.arguments.{version}+json'
        }

        response = self.upload_requests.post('/sessions/None/uploads', data=json.dumps(upload_job), headers=headers)

        if response.status_code == 406:
            raise ValueError(f'File already exists: {upload_job["fileName"]} in {upload_job["virtualPath"]} on {self.base_url}')

        if response.status_code == 201:
            upload_token = response.json()['uploadToken']
        else:
            raise RuntimeError(f'_start_asset_upload: {response.status_code} - {response.reason}: {response.text}')

        # TODO: assert response['state'] in ['Started']
        # TODO: this is in preparation for async version (see GameStop API - assets.py/contents.py)
        return {
            'upload_start': response,  # TODO: response.json() ?
            'upload_token': upload_token,
            'chunk_count': 0
        }

    def _cancel_file_upload_session(self, upload_token):
        try:
            response = self.upload_requests.delete(f'/sessions/None/uploads/{upload_token}')
        except:
            pass  # NOTE: ordinarily bad practice to except/pass, but this is called within a try/except so cannot throw

    def _upload_file(self, file, args):
        version = self.api_version.replace('/', '')

        session_token = args.get('sessionToken')
        upload_token = args.get('uploadToken')

        headers = {
            'Accept': f'application/vnd.bsn.content.upload.status.{version}+json'
        }
        if session_token:
            headers['Content-type'] = f'application/vnd.bsn.start.webpage.asset.upload.arguments.{version}+json'
        else:
            headers['Content-type'] = f'application/vnd.bsn.start.content.upload.arguments.{version}+json'

        body = {
            'fileName': args['fileName'],
            'fileSize': args['fileSize']
        }

        if 'relativePath' in args:
            body['relativePath'] = args['relativePath']
        if 'virtualPath' in args:
            body['virtualPath'] = args['virtualPath']

        url = f'/sessions/{session_token}/uploads/{upload_token}/'

        response = self.upload_requests.put(url, headers=headers, data=json.dumps(body))
        # TODO: assert response is okee-dokee

        with open(file, 'rb') as f:
            chunk_number = 0
            uploaded = 0
            while True:
                data = f.read(UPLOAD_CHUNK_SIZE)
                uploaded += len(data)
                if not data:
                    break

                headers = {
                    'Accept': 'application/vnd.bsn.error+json',
                    'Content-type': 'application/octet-stream'
                }
                chunk = self.upload_requests.post(
                    f'/sessions/{session_token}/uploads/{upload_token}/chunks?offset={chunk_number * UPLOAD_CHUNK_SIZE}',
                    data=data, headers=headers)
                chunk_number += 1

            # TODO:
            #        if not success:
            #            uploads_service.CancelFileUpload(args.UploadToken)
            #            raise RuntimeError(f'Failed to upload file: {args.FileName}')

            version = self.api_version.replace('/', '')

            headers = {
                'Accept': f'application/vnd.bsn.content.upload.status.{version}+json, '
                          f'application/vnd.bsn.content.upload.negotiation.status.{version}+json, '
                          'application/vnd.bsn.error+json',
            }

            if session_token:
                headers['Content-type'] = f'application/vnd.bsn.complete.webpage.asset.upload.arguments.{version}+json'
            else:
                headers['Content-type'] = f'application/vnd.bsn.complete.content.upload.arguments.{version}+json'

            upload_end = self.upload_requests.put(f'/sessions/{session_token}/uploads/{upload_token}',
                                      headers=headers, data=json.dumps(body))

            return upload_end.json().get('contentId')  # TODO: robustify!!
        # TODO:
        #    if not (status.State == 'Verified' or status.State == 'Completed'):
        #        raise RuntimeError(f'unable to complete upload for file: {args.FileName}')

    def _start_web_upload_session(self, body):
        version = self.api_version.replace('/', '')

        headers = {
            'Accept': f'application/vnd.bsn.webpage.upload.status.{version}+json, application/vnd.bsn.error+json',
            'Content-type': f'application/vnd.bsn.start.webpage.upload.arguments.{version}+json'
        }

        response = self.upload_requests.post('/sessions', headers=headers, data=json.dumps(body))
        # TODO: check status_code && content-type??
        # TODO: if response.is_json
        return response.json()

    def _cancel_web_upload_session(self, session_token):
        response = self.upload_requests.delete(f'/sessions/{session_token}')

    def _complete_web_upload_session(self, session):
        version = self.api_version.replace('/', '')

        headers = {
            'Content-type': f'application/vnd.bsn.complete.webpage.upload.arguments.{version}+json',
            'Accept': 'application/vnd.bsn.content.upload.status.pagedlist.201701+json, application/vnd.bsn.error+json'
        }

        body = json.dumps(session)

        response = self.upload_requests.put(f'/sessions/{session["sessionToken"]}', headers=headers, data=body)
        if not response.status_code == 406:  # TODO: robuster
            raise RuntimeError("didn't work")


    def __str__(self):
        s = f'{self.api_url}'
        if self.username:
            s += f' as {self.username}'
        return s
