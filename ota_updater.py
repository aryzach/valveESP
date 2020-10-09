import usocket
import os
import gc
import machine
import urequests

class OTAUpdater:

    def __init__(self, github_repo, ssid, password, module='', main_dir='main'):
        self.http_client = HttpClient()
        self.github_repo = github_repo.rstrip('/').replace('https://github.com', 'https://api.github.com/repos')
        self.main_dir = main_dir
        self.module = module.rstrip('/')
        self.ssid = ssid
        self.password = password

    def using_network(self):
        import network
        sta_if = network.WLAN(network.STA_IF)
        if not sta_if.isconnected():
            print('connecting to network...')
            sta_if.active(True)
            sta_if.connect(self.ssid, self.password)
            while not sta_if.isconnected():
                pass
        print('network config:', sta_if.ifconfig())

    def get_current_version(self):
        if 'version' in os.listdir(): 
            f = open('version')
            version = f.read()
            f.close()
            return version
        else:
            return '0.0'


    def check_for_update_to_install(self):
        print('Checking latest version... ')
        current_version = self.get_current_version()
        latest_version = self.get_latest_version()

        print('\tCurrent version: ', current_version)
        print('\tLatest version: ', latest_version)
        if latest_version > current_version:
            if 'version' in os.listdir():
                os.remove('version')
            f = open('version','w')
            f.write(latest_version)
            f.close()
            print('New version available, will download, install, and reboot') 
            self.download_install_reboot(latest_version)
 

    def download_install_reboot(self, latest_version):
        self.using_network()
        self.prep_download_main_file(self.github_repo + '/contents/' + self.main_dir, latest_version)
        print('Update installed (', latest_version, '), will reboot now')
        machine.reset()

    def get_latest_version(self):
        latest_release = self.http_client.get(self.github_repo + '/releases')
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
        version = latest_release.json()[0]['tag_name']
        latest_release.close()
        return version

    def prep_download_main_file(self, root_url, version):
        new_file = self.http_client.get(root_url + '/main.py')
        json = new_file.json()
        download_url = json['download_url']
        path = json['path'] 
        download_path = self.modulepath('main.py')
        self.download_main_file(download_url)


    def download_main_file(self, url):
        print(url)
        with open('main.py', 'w') as outfile:
            try:
                print('149')
                response = self.http_client.get(url)
                print('151')
                outfile.write(response.text)
            finally:
                response.close()
                outfile.close()
                gc.collect()


    def modulepath(self, path):
        return self.module + '/' + path if self.module else path


class Response:

    def __init__(self, f):
        self.raw = f
        self.encoding = 'utf-8'
        self._cached = None

    def close(self):
        if self.raw:
            self.raw.close()
            self.raw = None
        self._cached = None

    @property
    def content(self):
        if self._cached is None:
            try:
                self._cached = self.raw.read()
            finally:
                self.raw.close()
                self.raw = None
        return self._cached

    @property
    def text(self):
        return str(self.content, self.encoding)

    def json(self):
        import ujson
        return ujson.loads(self.content)


class HttpClient:

    def request(self, method, url, data=None, json=None, headers={}, stream=None):
        print('url: ',url)
        try:
            proto, dummy, host, path = url.split('/', 3)
        except ValueError:
            proto, dummy, host = url.split('/', 2)
            path = ''
        if proto == 'http:':
            port = 80
        elif proto == 'https:':
            import ussl
            port = 443
        else:
            raise ValueError('Unsupported protocol: ' + proto)

        if ':' in host:
            host, port = host.split(':', 1)
            port = int(port)


        ai = usocket.getaddrinfo(host, port)
        print(ai)
        ai = ai[0]
        print(ai)

        s = usocket.socket(ai[0], ai[1], ai[2])
        try:
            s.connect(ai[-1])
            if proto == 'https:':
                s = ussl.wrap_socket(s, server_hostname=host)
            s.write(b'%s /%s HTTP/1.0\r\n' % (method, path))
            if not 'Host' in headers:
                s.write(b'Host: %s\r\n' % host)
            # Iterate over keys to avoid tuple alloc
            for k in headers:
                s.write(k)
                s.write(b': ')
                s.write(headers[k])
                s.write(b'\r\n')
            # add user agent
            s.write('User-Agent')
            s.write(b': ')
            s.write('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36')
            s.write(b'\r\n')
            if json is not None:
                assert data is None
                import ujson
                data = ujson.dumps(json)
                s.write(b'Content-Type: application/json\r\n')
            if data:
                s.write(b'Content-Length: %d\r\n' % len(data))
            s.write(b'\r\n')
            if data:
                s.write(data)

            l = s.readline()
            print('readline l: ', l)
            l = l.split(None, 2)
            status = int(l[1])
            reason = ''
            if len(l) > 2:
                reason = l[2].rstrip()
            while True:
                l = s.readline()
                if not l or l == b'\r\n':
                    break
                # print(l)
                if l.startswith(b'Transfer-Encoding:'):
                    if b'chunked' in l:
                        raise ValueError('Unsupported ' + l)
                elif l.startswith(b'Location:') and not 200 <= status <= 299:
                    raise NotImplementedError('Redirects not yet supported')
        except OSError:
            s.close()
            raise

        resp = Response(s)
        print('initial: ', resp)
        resp.status_code = status
        resp.reason = reason
        print('final: ', resp)
        return resp


    def head(self, url, **kw):
        return self.request('HEAD', url, **kw)

    def get(self, url, **kw):
        return self.request('GET', url, **kw)
        #return self.req(url)

    def post(self, url, **kw):
        return self.request('POST', url, **kw)

    def put(self, url, **kw):
        return self.request('PUT', url, **kw)

    def patch(self, url, **kw):
        return self.request('PATCH', url, **kw)

    def delete(self, url, **kw):
        return self.request('DELETE', url, **kw)
