from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.normalization.vocabulary import CSE_FIELDS, CSE_PATH_TO_COLUMN

router = APIRouter()


@router.get("/cse")
def cse_schema(user: User = Depends(get_current_user)):
    return {
        "fields": [
            {
                "path": path,
                "column": CSE_PATH_TO_COLUMN.get(path, ""),
                "type": meta["type"],
                "required": meta["required"],
                "description": meta["desc"],
            }
            for path, meta in CSE_FIELDS.items()
        ],
        "version": "0.1.0",
        "notes": "Practical, OCSF-aligned canonical schema. Not full OCSF compliance.",
    }