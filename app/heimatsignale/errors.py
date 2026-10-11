"""Ein Fehlertyp für die gesamte API. Format siehe docs/API.md."""


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, fields: dict | None = None, **extra):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields
        self.extra = extra

    def body(self) -> dict:
        data = {"code": self.code, "message": self.message}
        if self.fields:
            data["fields"] = self.fields
        data.update(self.extra)
        return data


def not_found() -> ApiError:
    # Bewusst dieselbe Antwort für "gibt es nicht" und "darfst du nicht sehen".
    return ApiError(404, "not_found", "Das gibt es nicht oder es ist für dich nicht sichtbar.")


def validation(fields: dict) -> ApiError:
    return ApiError(422, "validation", "Bitte prüfe deine Eingaben.", fields=fields)
