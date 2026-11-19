"""Shared HTTP framing and delivery for the two local OCR review relays."""
from http.server import BaseHTTPRequestHandler

# Fixed vocabularies for response-write diagnostics; never raw exception data.
WRITE_PHASES = frozenset(('header_prepare', 'header_flush', 'body_write'))
WRITE_EXCEPTIONS = frozenset((
    'timeout', 'broken_pipe', 'connection_reset', 'connection_aborted',
    'other_os_error', 'other'))


def _write_category(exc):
    """Map an exception to a fixed category by built-in class only."""
    if isinstance(exc, TimeoutError):
        return 'timeout'
    if isinstance(exc, BrokenPipeError):
        return 'broken_pipe'
    if isinstance(exc, ConnectionResetError):
        return 'connection_reset'
    if isinstance(exc, ConnectionAbortedError):
        return 'connection_aborted'
    if isinstance(exc, OSError):
        return 'other_os_error'
    return 'other'


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
            phase = 'header_prepare'
            try:
                self.send_response(status)
                if not content_length_first:
                    self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                if content_length_first:
                    self.send_header('Content-Type', 'application/json')
                phase = 'header_flush'
                self.end_headers()
                phase = 'body_write'
                self.wfile.write(body)
            except Exception as exc:
                if latch is not None:
                    # Only a valid 200 response on a not-yet-halted relay is a
                    # trusted write failure; rejections never leave detail.
                    if status == 200 and not relay.halted:
                        relay.response_write_detail = (phase, _write_category(exc))
                    latch('response_write')
                    if isinstance(exc, TimeoutError):
                        # BaseHTTPRequestHandler may consume a timeout before
                        # HTTPServer.handle_error can halt the trusted lane.
                        relay.halted = True
                raise

    return Handler
