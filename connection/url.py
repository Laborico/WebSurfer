import socket
import ssl
from .variables import COOKIE_JAR


class URL:
    def __init__(self, url):
        self.scheme, url = url.split('://', 1)
        # Currently only support for http/1 will be implemented
        assert self.scheme in ['https', 'http']

        if '/' not in url:
            url += '/'

        self.host, path = url.split('/', 1)
        self.path = '/' + path

        if self.scheme == 'http':
            self.port = 80
        elif self.scheme == 'https':
            self.port = 443

        # Custom port handle
        if ':' in self.host:
            self.host, port = self.host.split(':', 1)
            self.port = int(port)

    def __str__(self):
        port_part = ':' + str(self.port)
        if self.scheme == 'https' and self.port == 443:
            port_part = ''
        if self.scheme == 'http' and self.port == 80:
            port_part = ''
        return self.scheme + '://' + self.host + port_part + self.path

    def request(self, referrer, payload=None):
        s = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
                )

        s.connect((self.host, self.port))

        if self.scheme == 'https':
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        method = 'POST' if payload else 'GET'
        # use \r\n for new lines, otherwise server will keep waiting for it
        # quirks from old protocols lol.
        request = '{} {} HTTP/1.0\r\n'.format(method, self.path)
        if payload:
            lenght = len(payload.encode('utf8'))
            request += 'Content-Length: {}\r\n'.format(lenght)
        request += 'Host: {}\r\n'.format(self.host)

        if self.host in COOKIE_JAR:
            cookie, params = COOKIE_JAR[self.host]
            allow_cookie = True
            if referrer and params.get('samesite', 'none') == 'lax':
                if method != 'GET':
                    allow_cookie = self.host == referrer.host
            if allow_cookie:
                request += 'Cookie: {}\r\n'.format(cookie)

        request += '\r\n'
        if payload:
            request += payload

        s.send(request.encode('utf8'))

        response = s.makefile('b')

        statusline = response.readline().decode('utf8')
        # gets http version, status and status message
        version, status, message = statusline.split(' ', 2)

        response_headers = {}
        while True:
            line = response.readline().decode('utf8')
            if line == '\r\n':
                break

            header, value = line.split(':', 1)
            response_headers[header.lower()] = value.strip()

        if 'set-cookie' in response_headers:
            cookie = response_headers['set-cookie']
            params = {}
            if ';' in cookie:
                cookie, rest = cookie.split(';', 1)
                for param in rest.split(';'):
                    if '=' in param:
                        param, value = param.split('=', 1)
                    else:
                        value = 'true'
                    params[param.strip().casefold()] = value.casefold()
            COOKIE_JAR[self.host] = (cookie, params)

        assert 'transfer-encoding' not in response_headers
        assert 'content-encoding' not in response_headers

        content = response.read()
        s.close()

        return response_headers, content

    # Resolves relative paths, specially for css style esheets
    def resolve(self, url):
        if '://' in url:
            return URL(url)
        if not url.startswith('/'):
            dir, _ = self.path.rsplit('/', 1)
            while url.startswith('../'):
                _, url = url.split('/', 1)
                if '/' in dir:
                    dir, _ = dir.rsplit('/', 1)
            url = dir + '/' + url

        if url.startswith('//'):
            return URL(self.scheme + ':' + url)
        else:
            return URL(self.scheme + '://' + self.host + ':' +
                       str(self.port) + url)

    def origin(self):
        return self.scheme + '://' + self.host + ':' + str(self.port)
