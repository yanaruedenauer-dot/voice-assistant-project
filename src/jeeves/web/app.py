from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI(title="Jeeves (Mock Pipeline)")


class Utterance(BaseModel):
    text: str
    lang: str = "en"


class Recommendation(BaseModel):
    name: str
    rationale: Dict[str, Any]


@app.post("/nlu/parse")
def parse(u: Utterance) -> Dict[str, Any]:
    intent = "book_restaurant" if "book" in u.text.lower() else "inform"
    slots: Dict[str, Any] = {}  # Typ deklariert
    sentiment = "neutral"
    return {"intent": intent, "slots": slots, "sentiment": sentiment}


@app.post("/recs")
def recs(u: Utterance) -> List[Recommendation]:
    return [
        Recommendation(
            name="Trattoria Ada",
            rationale={"distance": "0.8km", "wheelchair": True, "why": "fits prefs"},
        ),
        Recommendation(
            name="Green Bowl",
            rationale={
                "distance": "1.2km",
                "wheelchair": True,
                "why": "vegan friendly",
            },
        ),
    ]
