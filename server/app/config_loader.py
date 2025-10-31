import json
from models import GradeRequestConfig

def load_config_from_json_bytes(data: bytes) -> GradeRequestConfig:
    parsed = json.loads(data.decode("utf-8"))
    return GradeRequestConfig(**parsed)
