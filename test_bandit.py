import urllib.request
import hashlib
import ast

def test():
    # B310
    url = "https://example.com"
    urllib.request.urlopen(url) # nosec B310

    # B324
    hashlib.md5(b"test", usedforsecurity=False)

    # B307
    ast.literal_eval("{'a': 1}")

    # B615
    class Model:
        @staticmethod
        def from_pretrained(name, revision="main"):
            pass
    Model.from_pretrained("name", revision="main")

    # B608
    q = "SELECT * FROM table"
    return q
