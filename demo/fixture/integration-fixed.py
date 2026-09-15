import json


class IntegrationError(RuntimeError):
    pass


def decode_download(status: int, body: str):
    if not 200 <= status < 300:
        raise IntegrationError("Upstream returned {}: {}".format(status, body))
    try:
        return json.loads(body)
    except json.JSONDecodeError as error:
        raise IntegrationError("Upstream returned invalid JSON") from error
