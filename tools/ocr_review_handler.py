"""Shared HTTP framing and delivery for the two local OCR review relays."""
from http.server import BaseHTTPRequestHandler


def review_handler(relay, *, request_limit, timeout, error_body, latch=None,
                   content_length_first=False):
    """Bind the relay and caller's existing error and header policies."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            self.connection.settimeout(timeout)
            reason = 'request_framing'
            try:
                size = int(self.headers.get('Content-Length', '-1'))
                if not 0 < size <= request_limit or self.headers.get('Transfer-Encoding'):
                    raise ValueError()
                reason = 'request_read'
                raw = self.rfile.read(size)
                if len(raw) != size:
                    raise ValueError()
                reason = 'relay_rejected'
                body = relay.exchange(raw, self.headers.get('Authorization', ''), self.path)
                status = 200
            except Exception:
                if latch is not None:
                    latch(reason)
                relay.halted = True
                body, status = error_body, 400
            try:
                self.send_response(status)
                if not content_length_first:
                    self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                if content_length_first:
                    self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(body)
            except TimeoutError:
                # BaseHTTPRequestHandler may consume a timeout before
                # HTTPServer.handle_error can halt the trusted lane.
                if latch is not None:
                    latch('response_write')
                    relay.halted = True
                raise
            except Exception:
                if latch is not None:
                    latch('response_write')
                raise

    return Handler
