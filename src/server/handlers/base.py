"""Base request handler with CORS and JSON helpers."""

import json
import tornado.web


class BaseHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, x-requested-with")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def options(self):
        self.set_status(204)
        self.finish()

    def write_json(self, data):
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(data))

    def error_response(self, message, status=400):
        self.set_status(status)
        self.write_json({"error": message})

    def require_args(self, *args):
        values = {}
        for arg in args:
            value = self.get_argument(arg, None)
            if value is None:
                self.error_response(f"Missing required parameter: {arg}")
                return None
            values[arg] = value
        return values
