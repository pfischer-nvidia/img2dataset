import errno
import http
import socket
import sys
import urllib
from urllib.error import URLError

import dns.resolver

resolver = dns.resolver.Resolver(configure=False)
resolver.nameservers = [
    "8.8.8.8",
    "2001:4860:4860::8888",
    "8.8.4.4",
    "2001:4860:4860::8844",
]


def custom_resolve(host):
    result = resolver.resolve(host)
    ips = [ns.to_text() for ns in result]
    if len(ips) < 1:
        raise URLError(f"Custom DNS: No addresses found for {host}")
    return ips[0]


class MyHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        """Connect to the host and port specified in __init__."""
        sys.audit("http.client.connect", self, self.host, self.port)
        self.sock = self._create_connection(
            (custom_resolve(self.host), self.port), self.timeout, self.source_address
        )
        # Might fail in OSs that don't implement TCP_NODELAY
        try:
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError as e:
            if e.errno != errno.ENOPROTOOPT:
                raise

        if self._tunnel_host:
            self._tunnel()


class MyHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        "Connect to a host on a given (SSL) port."

        # super().connect()

        sys.audit("http.client.connect", self, self.host, self.port)
        self.sock = self._create_connection(
            (custom_resolve(self.host), self.port), self.timeout, self.source_address
        )
        # Might fail in OSs that don't implement TCP_NODELAY
        try:
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError as e:
            if e.errno != errno.ENOPROTOOPT:
                raise

        if self._tunnel_host:
            self._tunnel()

        # end super().connect()

        if self._tunnel_host:
            server_hostname = self._tunnel_host
        else:
            server_hostname = self.host

        self.sock = self._context.wrap_socket(
            self.sock, server_hostname=server_hostname
        )


class MyHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(MyHTTPConnection, req)


class MyHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(MyHTTPSConnection, req)


def install_custom_dns():
    opener = urllib.request.build_opener(MyHTTPHandler, MyHTTPSHandler)
    urllib.request.install_opener(opener)


if __name__ == "__main__":
    import ssl
    import io

    install_custom_dns()

    url = "https://www.ssllabs.com"

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    request = urllib.request.Request(url, data=None)
    with urllib.request.urlopen(request, timeout=5, context=ctx) as r:
        data = r.read()
        print(data)