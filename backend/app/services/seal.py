import hashlib
import json


class SealService:
    def generate_hash(self, data: dict, previous_hash: str | None = None) -> str:
        payload = json.dumps(data, sort_keys=True, ensure_ascii=True)
        if previous_hash:
            payload = previous_hash + payload
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def verify(self, data: dict, expected_hash: str, previous_hash: str | None = None) -> bool:
        actual_hash = self.generate_hash(data, previous_hash)
        return actual_hash == expected_hash
