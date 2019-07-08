#!/usr/bin/env python3
# pylint: disable=W0612, W0702, R1702, W0122
""" Basic HTTP file server """

import socket
import sys
import traceback
import pathlib
import mimetypes
import contextlib
from io import StringIO


@contextlib.contextmanager
def stdout_io(stdout=None):
    """ Redirects stdout so we can capture it """
    old = sys.stdout
    if stdout is None:
        stdout = StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old


def response_ok(body=b"This is a minimal response", mimetype=b"text/plain"):
    """
    returns a basic HTTP response
    Ex:
        response_ok(
            b"<html><h1>Welcome:</h1></html>",
            b"text/html"
        ) ->

        b'''
        HTTP/1.1 200 OK\r\n
        Content-Type: text/html\r\n
        \r\n
        <html><h1>Welcome:</h1></html>\r\n
        '''
    """

    return b"\r\n".join([
        b"HTTP/1.1 200 OK",
        b"Content-Type: " + mimetype,
        b"",
        body,
    ])


def response_method_not_allowed():
    """Returns a 405 Method Not Allowed response"""

    return b"\r\n".join([
        b"HTTP/1.1 405 Method Not Allowed",
        b"",
        b"You can't do that on this server!",
    ])


def response_not_found():
    """Returns a 404 Not Found response"""

    return b"\r\n".join([
        b"HTTP/1.1 404 Not Found",
    ])


def parse_request(request):
    """
    Given the content of an HTTP request, returns the path of that request.

    This server only handles GET requests, so this method shall raise a
    NotImplementedError if the method of the request is not GET.
    """

    method, path, version = request.split("\r\n")[0].split(" ")

    if method != "GET":
        raise NotImplementedError

    return path


def response_path(path):
    """
    This method should return appropriate content and a mime type.

    If the requested path is a directory, then the content should be a
    plain-text listing of the contents with mimetype `text/plain`.

    If the path is a file, it should return the contents of that file
    and its correct mimetype.

    If the path does not map to a real location, it should raise an
    exception that the server can catch to return a 404 response.

    Ex:
        response_path('/a_web_page.html') -> (b"<html><h1>North Carolina...",
                                            b"text/html")

        response_path('/images/sample_1.png')
                        -> (b"A12BCF...",  # contents of sample_1.png
                            b"image/png")

        response_path('/') -> (b"images/, a_web_page.html, make_type.py,...",
                             b"text/plain")

        response_path('/a_page_that_doesnt_exist.html') -> Raises a NameError

    """
    content = ""
    mime_type = ""

    # We're going to exec user input - which is generally a terrible idea.
    #   So here's a check to make sure they're not trying to kill us.
    # valid_scripts = ['make_time.py', 'this_script_should_not_run.py']
    valid_scripts = ["make_time.py"]

    try:
        mime_type = mimetypes.MimeTypes().guess_type("./webroot/" + path)[0]

        if mime_type is None:  # Directory
            mime_type = "text/plain"
        mime_type = mime_type.encode()

        open_path = pathlib.Path("./webroot/" + path)
        for child in open_path.iterdir():
            content += str(child)[8:] + "\r\n"
        content = content.encode()

    except FileNotFoundError:
        raise NameError

    except NotADirectoryError:
        if path[-3:] == ".py" and path[1:] in valid_scripts:
            content, mime_type = run_python_script(path)
        else:
            with open(("./webroot/" + path), "rb") as open_file:
                content = open_file.read()

    return content, mime_type


def run_python_script(path):
    """
    Python script requested, let's run it, what could go wrong?
    """

    with stdout_io() as output:
        exec(open("./webroot" + path).read())

    content = output.getvalue().encode()
    mime_type = b"text/html"

    return content, mime_type


def server(log_buffer=sys.stderr):
    """ HTTP Server """
    address = ("127.0.0.1", 10000)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print("making a server on {0}:{1}".format(*address), file=log_buffer)
    sock.bind(address)
    sock.listen(1)

    try:
        while True:
            print("waiting for a connection", file=log_buffer)
            conn, addr = sock.accept()  # blocking
            try:
                print("connection - {0}:{1}".format(*addr), file=log_buffer)

                request = ""
                while True:
                    data = conn.recv(1024)
                    request += data.decode("utf8")

                    if "\r\n\r\n" in request:
                        break

                print("Request received:\n{}\n\n".format(request))

                try:
                    path = parse_request(request)
                    body, mimetype = response_path(path)

                    response = response_ok(body=body, mimetype=mimetype)

                except NotImplementedError:
                    response = response_method_not_allowed()

                except NameError:
                    response = response_not_found()

                conn.sendall(response)
            except:
                traceback.print_exc()
            finally:
                conn.close()

    except KeyboardInterrupt:
        sock.close()
        return
    except:
        traceback.print_exc()


if __name__ == "__main__":
    server()
    sys.exit(0)
