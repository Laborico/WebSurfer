import socket
import ssl


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

    def request(self):
        s = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
                )

        s.connect((self.host, self.port))

        if self.scheme == 'https':
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        # use \r\n for new lines, otherwise server will keep waiting for it
        # quirks from old protocols lol.
        request = 'GET {} HTTP/1.0\r\n'.format(self.path)
        request += 'Host: {}\r\n'.format(self.host)
        request += '\r\n'

        s.send(request.encode('utf8'))

        response = s.makefile('r', encoding='utf8', newline='\r\n')

        statusline = response.readline()
        # gets http version, status and status message
        version, status, message = statusline.split(' ', 2)

        response_headers = {}
        while True:
            line = response.readline()
            if line == '\r\n':
                break

            header, value = line.split(':', 1)
            response_headers[header.lower()] = value.strip()

        assert 'transfer-encoding' not in response_headers
        assert 'content-encoding' not in response_headers

        content = response.read()
        s.close()

        return content

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
