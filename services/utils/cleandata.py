import unicodedata
from fastapi import HTTPException


def clean_data(raw: str):
    stringy = unicodedata.normalize("NFKC", (raw or "")).strip()
    if not (1 <= len(stringy) <= 64):
        # print("out of lengthy")
        raise HTTPException(
            400,
            "the name you have given me is simply too long, or simply too short. or nonexistant",
        )
    if any(unicodedata.category(c).startswith("C") for c in stringy):
        # print("controlly chars ew")
        raise HTTPException(400, "name has control characters smh")
    return stringy


# print(clean_data("gshetryhgegsrdSFDGEFsdfd%^yg"))
