import socket


class URL:
    def __init__(self, url):
        self.scheme, url = url.split('://', 1)
        # Currently only support for http/1 will be implemented
        assert self.scheme == 'http'

        if '/' not in url:
            url += '/'

        self.host, path = url.split('/', 1)
        self.path = '/' + path

    def request(self):
        s = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
                )
        s.connect((self.host, 80))

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


# Basic html renderer (printer?)
def show(body):
    in_tag = False

    for c in body:
        if c == '<':
            in_tag = True
        elif c == '>':
            in_tag = False
        elif not in_tag:
            print(c, end='')


def load(url):
    body = url.request()
    show(body)


if __name__ == '__main__':
    import sys

    load(URL(sys.argv[1]))
