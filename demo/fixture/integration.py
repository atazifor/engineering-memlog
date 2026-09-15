import json


class IntegrationError(RuntimeError):
    pass


def decode_download(status: int, body: str):
    try:
        return json.loads(body)
    except json.JSONDecodeError as error:
        raise IntegrationError("Unable to read JSON returned by upstream") from error
