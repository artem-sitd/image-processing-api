from fastapi import File, Form, UploadFile
from pydantic import BaseModel


class UploadInputSchema(BaseModel):
    file: UploadFile
    project_id: int

    @classmethod
    def as_form(cls, project_id: int = Form(...), file: UploadFile = File(...)):
        return cls(project_id=project_id, file=file)
