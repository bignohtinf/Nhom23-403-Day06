import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"


def load_json(filename: str):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


cars = load_json("cars.json")
maintenance = load_json("maintenance.json")
reviews = load_json("reviews_processed.json")


def parse_intent(text: str):
    lower = text.lower()
    budget_match = re.search(r"(\d+)\s*(trieu|tr|m|ty|tỷ)?", lower)
    budget_million = None
    if budget_match:
        number = int(budget_match.group(1))
        unit = budget_match.group(2) or ""
        budget_million = number * 1000 if unit in {"ty", "tỷ"} else number

    family_match = re.search(r"gia d[iì]nh\s*(\d+)", lower)
    family_size = int(family_match.group(1)) if family_match else None

    usage = "mixed"
    if "nội thành" in lower or "noi thanh" in lower:
        usage = "city"
    elif "cao tốc" in lower or "cao toc" in lower or "đường dài" in lower:
        usage = "highway"

    no_charging = (
        "không có chỗ sạc" in lower
        or "khong co cho sac" in lower
        or "chua co cho sac" in lower
    )

    return {
        "budget_million": budget_million,
        "family_size": family_size,
        "usage": usage,
        "has_home_charging": not no_charging,
    }


def score_car(car: dict, intent: dict):
    score = 0
    reasons = []

    budget = intent["budget_million"]
    if budget is not None:
        if car["price_million"] <= budget:
            score += 3
            reasons.append("Nam trong ngan sach")
        elif car["price_million"] <= budget + 150:
            score += 1
            reasons.append("Vuot ngan sach nhe")
        else:
            score -= 2
            reasons.append("Vuot ngan sach kha xa")

    family_size = intent["family_size"]
    if family_size is not None:
        if family_size >= 5 and car["seats"] >= 7:
            score += 3
            reasons.append("Phu hop gia dinh dong nguoi")
        elif family_size <= 4 and car["seats"] <= 5:
            score += 2
            reasons.append("Phu hop gia dinh nho")

    length_mm = car.get("size_mm", {}).get("length", 0)
    range_km = car.get("range_km_per_full_charge", 0)

    if intent["usage"] == "city":
        if length_mm and length_mm <= 4300:
            score += 2
            reasons.append("Kich thuoc gon de di noi thanh")
        else:
            score -= 0.5
            reasons.append("Xe lon hon, xoay tro noi thanh kem hon")
    elif intent["usage"] == "highway":
        if range_km >= 430:
            score += 2
            reasons.append("Tam di chuyen phu hop duong dai")
        else:
            score += 0.5
            reasons.append("Tam di chuyen o muc vua phai")

    if not intent["has_home_charging"]:
        score -= 1
        reasons.append("Can can nhac ha tang sac tai nha")

    return score, reasons


def recommend(user_text: str):
    intent = parse_intent(user_text)
    scored = []
    for car in cars:
        score, reasons = score_car(car, intent)
        scored.append({"car": car, "score": score, "reasons": reasons})
    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:3]

    model_names = [x["car"]["model"] for x in top]
    review_map = {r["model"]: r for r in reviews if r["model"] in model_names}
    maintenance_map = {m["model"]: m for m in maintenance if m["model"] in model_names}

    return intent, top, review_map, maintenance_map


def build_fallback_answer(intent, top, review_map, maintenance_map):
    lines = []
    lines.append("Goi y top xe VinFast:")
    for idx, item in enumerate(top[:2], start=1):
        model = item["car"]["model"]
        lines.append(f"{idx}. {model} (score: {round(item['score'], 2)})")
        if item["reasons"]:
            lines.append(f"   - Ly do: {', '.join(item['reasons'])}")
        if model in review_map:
            lines.append(f"   - Pros: {', '.join(review_map[model]['pros'])}")
            lines.append(f"   - Cons: {', '.join(review_map[model]['cons'])}")
        if model in maintenance_map:
            lines.append(f"   - Bao duong: {maintenance_map[model]['maintenance']}")
    lines.append(f"Intent da hieu: {intent}")
    return "\n".join(lines)


def ask_llm(user_text: str, intent, top, review_map, maintenance_map):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None, "No OPENAI_API_KEY, fallback to rule-based answer."

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    client = OpenAI(api_key=api_key)

    payload = {
        "user_query": user_text,
        "intent": intent,
        "top_candidates": [
            {
                "model": x["car"]["model"],
                "model_version": x["car"].get("model_version"),
                "type": x["car"].get("type"),
                "price_million": x["car"]["price_million"],
                "range_km_per_full_charge": x["car"].get("range_km_per_full_charge"),
                "charge_time_min": x["car"].get("charge_time_min"),
                "score": round(x["score"], 2),
                "reasons": x["reasons"],
            }
            for x in top
        ],
        "reviews": review_map,
        "maintenance": maintenance_map,
    }

    system_prompt = (
        "Ban la chatbot VinFast. Tra loi bang tieng Viet, ngan gon, de demo. "
        "Phan biet ro fact (du lieu xe) va opinion (review). "
        "Dua ra 2-3 goi y xe, ly do, pros/cons va nhac bao duong co ban."
    )

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    )
    return resp.output_text, None


def main():
    load_dotenv(BASE_DIR / ".env")
    print("VinFast AI Chatbot (CLI) - type 'exit' to quit.")
    print("Vi du: Toi co 800 trieu, gia dinh 4 nguoi, di noi thanh.")

    while True:
        user_text = input("\nYou: ").strip()
        if not user_text:
            continue
        if user_text.lower() in {"exit", "quit"}:
            print("Bye.")
            break

        intent, top, review_map, maintenance_map = recommend(user_text)
        llm_answer, err = ask_llm(user_text, intent, top, review_map, maintenance_map)

        if llm_answer:
            print(f"\nBot:\n{llm_answer}")
        else:
            print("\nBot (fallback):")
            print(build_fallback_answer(intent, top, review_map, maintenance_map))
            print(f"\n[Note] {err}")


if __name__ == "__main__":
    main()
