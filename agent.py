from __future__ import annotations

import json
import os
import re
import textwrap
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BOOKING_DIR = BASE_DIR / "thongtindatlich"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 20

VINFAST_WARRANTY_URL = "https://vinfastauto.com/vn_vi/thong-tin-bao-hanh"
VINFAST_POLICY_URL = "https://vinfastauto.com/vn_vi/hop-dong-va-chinh-sach/chinh-sach"
VINFAST_SHOWROOM_URL = "https://vinfastauto.com/vn_vi/tim-kiem-showroom-tram-sac"
VINFAST_DEPOSIT_LIST_URL = "https://shop.vinfastauto.com/vn_vi/dat-coc-o-to-dien-vinfast.html"
VINFAST_HOTLINE = "1900 23 23 89"

OFFICIAL_MODEL_URLS: Dict[str, str] = {
    "vf 3": "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-vf3.html",
    "vf3": "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-vf3.html",
    "vf 5": "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-dien-vf5.html",
    "vf5": "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-dien-vf5.html",
    "vf 6": "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-dien-vf6.html",
    "vf6": "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-dien-vf6.html",
    "vf 7": "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-dien-vf7.html",
    "vf7": "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-dien-vf7.html",
    "vf 8": "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-vf8.html",
    "vf8": "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-vf8.html",
    "vf 9": "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-vf9.html",
    "vf9": "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-vf9.html",
    "minio green": "https://vinfastauto.com/vn_vi/minio-green",
    "herio green": "https://vinfastauto.com/vn_vi/herio-green",
    "nerio green": "https://shop.vinfastauto.com/vn_vi/nerio-green.html",
    "limo green": "https://vinfastauto.com/vn_vi/limo-green",
    "ec van": "https://shop.vinfastauto.com/vn_vi/vinfast-ecvan.html",
    "ebus": "https://shop.vinfastauto.com/vn_vi/ebus.html",
    "vf mpv 7": "https://shop.vinfastauto.com/vn_vi/dat-coc-o-to-dien-vinfast.html",
}


def load_json(filename: str) -> Any:
    path = DATA_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(text: str) -> str:
    text = text or ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def compact_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def vn_money_million(value: Any) -> str:
    if value is None:
        return "chưa có giá trong data nội bộ"
    return f"{int(round(float(value))):,} triệu VNĐ".replace(",", ".")


def first_non_empty(*values: Any) -> Optional[Any]:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


CARS: List[Dict[str, Any]] = load_json("cars.json")
MAINTENANCE: List[Dict[str, Any]] = load_json("maintenance.json")
REVIEWS: List[Dict[str, Any]] = load_json("reviews_processed.json")


for car in CARS:
    car["_model_key"] = normalize_text(f"{car.get('model', '')} {car.get('model_version', '')}")
    car["_display_name"] = " ".join(
        part for part in [car.get("model", "").strip(), car.get("model_version", "").strip()] if part
    )


for item in MAINTENANCE:
    item["_model_key"] = normalize_text(item.get("model", ""))

for item in REVIEWS:
    item["_model_key"] = normalize_text(item.get("model", ""))


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def find_matching_cars(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    q = normalize_text(query)
    if not q:
        return []

    scored: List[Tuple[float, Dict[str, Any]]] = []
    for car in CARS:
        model = normalize_text(car.get("model", ""))
        full_name = car["_model_key"]
        score = 0.0

        if q == model or q == full_name:
            score = 1.0
        elif q in full_name:
            score = 0.95
        elif model in q:
            score = 0.9
        else:
            score = max(similarity(q, full_name), similarity(q, model))

        scored.append((score, car))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [car for score, car in scored if score >= 0.45][:top_k]


MODEL_ALIASES = {
    "vf3": "VF 3",
    "vf 3": "VF 3",
    "vf5": "VF 5",
    "vf 5": "VF 5",
    "vf5 plus": "VF 5",
    "vf6": "VF 6",
    "vf 6": "VF 6",
    "vf7": "VF 7",
    "vf 7": "VF 7",
    "vf8": "VF 8",
    "vf 8": "VF 8",
    "vf9": "VF 9",
    "vf 9": "VF 9",
    "mpv 7": "VF MPV 7",
    "vf mpv 7": "VF MPV 7",
    "minio": "Minio Green",
    "herio": "Herio Green",
    "nerio": "Nerio Green",
    "limo": "Limo Green",
    "ecvan": "EC Van",
    "ec van": "EC Van",
}


def canonical_model_name(text: str) -> str:
    key = normalize_text(text)
    return MODEL_ALIASES.get(key, text.strip())


class UserNeed(Dict[str, Any]):
    pass


def parse_budget_million(text: str) -> Optional[float]:
    lowered = normalize_text(text)
    matches = re.findall(r"(\d+(?:[\.,]\d+)?)\s*(ty|trieu|tr|m)\b", lowered)
    if matches:
        raw_number, unit = matches[0]
        number = float(raw_number.replace(",", "."))
        if unit == "ty":
            return number * 1000
        return number

    plain_num = re.search(r"\b(\d{3,4})\b", lowered)
    if plain_num:
        candidate = int(plain_num.group(1))
        if 180 <= candidate <= 2500:
            return float(candidate)
    return None


def parse_user_need(text: str) -> Dict[str, Any]:
    lowered = normalize_text(text)
    family_size = None
    seats_required = None

    family_match = re.search(r"(gia dinh|nhom)\s*(\d+)", lowered)
    if family_match:
        family_size = int(family_match.group(2))

    seats_match = re.search(r"(\d+)\s*(cho|ghe)", lowered)
    if seats_match:
        seats_required = int(seats_match.group(1))

    need = {
        "budget_million": parse_budget_million(text),
        "family_size": family_size,
        "seats_required": seats_required,
        "has_home_charging": not any(
            phrase in lowered
            for phrase in [
                "khong co cho sac",
                "chua co cho sac",
                "khong lap duoc tru sac",
                "khong co san cho sac",
            ]
        ),
        "wants_service_vehicle": any(
            phrase in lowered for phrase in ["chay dich vu", "grab", "taxi", "kinh doanh van tai", "xe dich vu"]
        ),
        "needs_delivery_van": any(
            phrase in lowered for phrase in ["giao hang", "cho hang", "van chuyen hang", "ship hang", "xe van"]
        ),
        "needs_city_car": any(
            phrase in lowered for phrase in ["noi thanh", "di pho", "do thi", "di lam", "di hoc", "luon lach"]
        ),
        "needs_long_range": any(
            phrase in lowered for phrase in ["duong dai", "cao toc", "ve que", "di xa", "xuyen tinh", "di tinh"]
        ),
        "needs_big_family": any(
            phrase in lowered for phrase in ["7 cho", "dong nguoi", "3 the he", "gia dinh lon"]
        ),
        "prefers_low_budget": any(
            phrase in lowered for phrase in ["re nhat", "tiet kiem", "gia mem", "duoi 500", "duoi 600"]
        ),
    }
    return need


def group_key(car: Dict[str, Any]) -> str:
    return normalize_text(car.get("model", ""))


def review_for_car(car: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    candidates = []
    car_full = normalize_text(car["_display_name"])
    model_only = normalize_text(car.get("model", ""))
    for item in REVIEWS:
        score = max(similarity(car_full, item["_model_key"]), similarity(model_only, item["_model_key"]))
        candidates.append((score, item))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1] if candidates and candidates[0][0] >= 0.5 else None


def maintenance_for_car(car: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    candidates = []
    car_full = normalize_text(car["_display_name"])
    model_only = normalize_text(car.get("model", ""))
    for item in MAINTENANCE:
        score = max(similarity(car_full, item["_model_key"]), similarity(model_only, item["_model_key"]))
        candidates.append((score, item))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1] if candidates and candidates[0][0] >= 0.45 else None


def score_car(car: Dict[str, Any], need: Dict[str, Any]) -> Tuple[float, List[str]]:
    score = 0.0
    reasons: List[str] = []
    price = car.get("price_million")
    seats = safe_float(car.get("seats"), 0)
    range_km = safe_float(car.get("range_km_per_full_charge"), 0)
    length_mm = safe_float(car.get("size_mm", {}).get("length"), 0)
    car_type = normalize_text(f"{car.get('type', '')} {car.get('model', '')} {car.get('model_version', '')}")

    budget = need.get("budget_million")
    if budget is not None:
        if price is None:
            score -= 0.4
            reasons.append("data giá đang thiếu nên khó chốt theo ngân sách")
        elif price <= budget:
            score += 3.0
            reasons.append("nằm trong ngân sách")
        elif price <= budget * 1.1 + 60:
            score += 1.0
            reasons.append("vượt ngân sách nhẹ nhưng vẫn có thể cân nhắc")
        else:
            score -= 2.5
            reasons.append("vượt ngân sách khá xa")

    seats_required = need.get("seats_required")
    family_size = need.get("family_size")
    target_seats = max(filter(None, [seats_required, family_size or 0]), default=0)
    if target_seats:
        if seats >= target_seats:
            score += 2.2
            reasons.append(f"đủ chỗ cho nhu cầu {int(target_seats)} người")
        else:
            score -= 2.0
            reasons.append("số chỗ có thể không đủ")

    if need.get("needs_city_car"):
        if length_mm and length_mm <= 4300:
            score += 1.8
            reasons.append("kích thước gọn, hợp đi phố")
        elif length_mm:
            score -= 0.5
            reasons.append("thân xe lớn hơn, xoay trở phố đông kém hơn")

    if need.get("needs_long_range"):
        if range_km >= 500:
            score += 2.0
            reasons.append("tầm hoạt động tốt cho đường dài")
        elif range_km >= 350:
            score += 1.0
            reasons.append("tầm hoạt động ở mức ổn cho nhu cầu đi xa vừa phải")
        else:
            score -= 1.0
            reasons.append("tầm hoạt động chưa thật sự tối ưu cho đường dài")

    if need.get("needs_big_family"):
        if seats >= 7:
            score += 2.0
            reasons.append("phù hợp gia đình đông người")
        else:
            score -= 1.2
            reasons.append("không phải cấu hình tối ưu cho gia đình lớn")

    if need.get("wants_service_vehicle"):
        if "dich vu" in car_type or car.get("model") in {"Herio Green", "Nerio Green", "Limo Green"}:
            score += 2.4
            reasons.append("đúng nhóm xe dịch vụ")
        elif car.get("model") == "VF 5":
            score += 1.3
            reasons.append("cũng là lựa chọn phổ biến cho dịch vụ")

    if need.get("needs_delivery_van"):
        if car.get("model") == "EC Van":
            score += 3.0
            reasons.append("thiết kế đúng bài toán giao hàng nội đô")
        else:
            score -= 1.5
            reasons.append("không phải cấu hình tối ưu cho chở hàng")

    if not need.get("has_home_charging", True):
        if range_km >= 450:
            score += 0.8
            reasons.append("tầm chạy tốt hơn khi chưa có chỗ sạc tại nhà")
        else:
            score -= 0.6
            reasons.append("nên cân nhắc kỹ hạ tầng sạc nếu chưa có sạc tại nhà")

    if need.get("prefers_low_budget") and price is not None and price <= 500:
        score += 1.2
        reasons.append("chi phí tiếp cận dễ chịu")

    return score, reasons


def pick_recommendations(user_need_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
    need = parse_user_need(user_need_text)
    scored: List[Dict[str, Any]] = []
    for car in CARS:
        score, reasons = score_car(car, need)
        scored.append({"car": car, "score": score, "reasons": reasons})

    scored.sort(key=lambda x: (x["score"], safe_float(x["car"].get("range_km_per_full_charge"), 0)), reverse=True)

    unique: List[Dict[str, Any]] = []
    seen_groups = set()
    for item in scored:
        key = group_key(item["car"])
        if key in seen_groups:
            continue
        unique.append(item)
        seen_groups.add(key)
        if len(unique) >= top_k:
            break
    return unique


def format_car_fact_block(car: Dict[str, Any]) -> str:
    colors = car.get("color") or []
    return textwrap.dedent(
        f"""
        - Mẫu: {car['_display_name']}
        - Loại xe: {car.get('type', 'chưa rõ')}
        - Giá: {vn_money_million(car.get('price_million'))}
        - Số chỗ: {first_non_empty(car.get('seats'), 'chưa rõ')}
        - Tầm chạy/lần sạc: {first_non_empty(car.get('range_km_per_full_charge'), 'chưa rõ')} km
        - Sạc nhanh 10-70%: {first_non_empty(car.get('charge_time_min'), 'chưa rõ')} phút
        - Kích thước D x R x C: {car.get('size_mm', {}).get('length', 'N/A')} x {car.get('size_mm', {}).get('width', 'N/A')} x {car.get('size_mm', {}).get('height', 'N/A')} mm
        - Màu tiêu biểu: {', '.join(colors[:6]) if colors else 'chưa có dữ liệu'}
        """
    ).strip()


def official_url_for_model(text: str) -> Optional[str]:
    q = normalize_text(text)
    if q in OFFICIAL_MODEL_URLS:
        return OFFICIAL_MODEL_URLS[q]
    for key, url in OFFICIAL_MODEL_URLS.items():
        if key in q or q in key:
            return url
    return None


def fetch_clean_text(url: str, max_chars: int = 5000) -> str:
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = compact_whitespace(" ".join(soup.stripped_strings))
        return text[:max_chars]
    except Exception as exc:
        return f"[Không tải được {url}: {exc}]"


def ddg_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    try:
        url = "https://html.duckduckgo.com/html/"
        response = requests.get(url, params={"q": query}, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        results: List[Dict[str, str]] = []
        for item in soup.select(".result"):
            a_tag = item.select_one(".result__title a") or item.select_one("a.result__a")
            snippet = item.select_one(".result__snippet")
            if not a_tag:
                continue
            title = compact_whitespace(a_tag.get_text(" ", strip=True))
            href = a_tag.get("href", "")
            body = compact_whitespace(snippet.get_text(" ", strip=True) if snippet else "")
            if title and href:
                results.append({"title": title, "url": href, "snippet": body})
            if len(results) >= max_results:
                break
        return results
    except Exception:
        return []


def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if tavily_api_key:
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                },
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            output = []
            for item in data.get("results", [])[:max_results]:
                output.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": compact_whitespace(item.get("content", "")),
                    }
                )
            if output:
                return output
        except Exception:
            pass
    return ddg_search(query, max_results=max_results)


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("84") and len(digits) >= 11:
        digits = "0" + digits[2:]
    return digits


def is_valid_phone(phone: str) -> bool:
    digits = normalize_phone(phone)
    return bool(re.fullmatch(r"0\d{9,10}", digits))


def slugify_filename(text: str) -> str:
    text = normalize_text(text)
    return re.sub(r"\s+", "-", text).strip("-") or "khach-hang"


def ensure_booking_dir() -> None:
    BOOKING_DIR.mkdir(parents=True, exist_ok=True)


@tool("vinfast_recommendation")
def vinfast_recommendation(user_need: str) -> str:
    """Tư vấn mẫu xe VinFast phù hợp theo ngân sách, số người, kiểu sử dụng và điều kiện sạc."""
    need = parse_user_need(user_need)
    picks = pick_recommendations(user_need, top_k=3)
    lines = ["TÓM TẮT NHU CẦU:", json.dumps(need, ensure_ascii=False, indent=2), "", "GỢI Ý XE:"]

    for idx, item in enumerate(picks, start=1):
        car = item["car"]
        review = review_for_car(car)
        maint = maintenance_for_car(car)
        lines.append(f"{idx}. {car['_display_name']} | score={round(item['score'], 2)}")
        lines.append(f"   - Giá: {vn_money_million(car.get('price_million'))}")
        lines.append(f"   - Tầm chạy: {first_non_empty(car.get('range_km_per_full_charge'), 'chưa rõ')} km")
        lines.append(f"   - Lý do: {', '.join(item['reasons']) if item['reasons'] else 'phù hợp tổng thể'}")
        if review:
            pros = "; ".join(review.get("pros", [])[:3])
            cons = "; ".join(review.get("cons", [])[:2])
            lines.append(f"   - Pros từ review: {pros or 'chưa có'}")
            lines.append(f"   - Cons từ review: {cons or 'chưa có'}")
        if maint:
            warranty = maint.get("warranty", {}).get("vehicle", {}).get("personal_use", {}).get("duration")
            battery = maint.get("warranty", {}).get("battery", {}).get("personal_use", {}).get("duration")
            if warranty or battery:
                lines.append(
                    f"   - Bảo hành tham khảo trong data: xe={warranty or 'chưa rõ'} | pin={battery or 'chưa rõ'}"
                )
        official_url = official_url_for_model(car.get("model", ""))
        if official_url:
            lines.append(f"   - Link chính thức: {official_url}")
        lines.append("")

    return "\n".join(lines).strip()


@tool("vinfast_specs_lookup")
def vinfast_specs_lookup(model_query: str) -> str:
    """Tra cứu thông số, phiên bản, màu sắc, review và bảo hành của một mẫu xe VinFast."""
    matches = find_matching_cars(canonical_model_name(model_query), top_k=5)
    if not matches:
        return f"Không tìm thấy mẫu xe phù hợp với truy vấn: {model_query}"

    lines: List[str] = []
    for car in matches:
        lines.append(format_car_fact_block(car))
        review = review_for_car(car)
        maint = maintenance_for_car(car)
        if review:
            lines.append(f"- Pros review: {'; '.join(review.get('pros', [])[:4])}")
            lines.append(f"- Cons review: {'; '.join(review.get('cons', [])[:3])}")
        if maint:
            vehicle_warranty = maint.get("warranty", {}).get("vehicle", {}).get("personal_use", {}).get("duration")
            battery_warranty = maint.get("warranty", {}).get("battery", {}).get("personal_use", {}).get("duration")
            capacity_commitment = maint.get("warranty", {}).get("battery", {}).get("capacity_commitment")
            lines.append(
                f"- Bảo hành trong data nhóm: xe={vehicle_warranty or 'chưa rõ'} | pin={battery_warranty or 'chưa rõ'} | cam kết dung lượng pin={capacity_commitment or 'chưa rõ'}"
            )
        official_url = official_url_for_model(car.get("model", ""))
        if official_url:
            lines.append(f"- Link chính thức: {official_url}")
        lines.append("")
    return "\n".join(lines).strip()


@tool("vinfast_compare")
def vinfast_compare(models_csv: str) -> str:
    """So sánh nhanh 2-4 mẫu xe VinFast. Đầu vào là chuỗi tên xe ngăn cách bằng dấu phẩy."""
    raw_models = [canonical_model_name(x) for x in models_csv.split(",") if x.strip()]
    selected: List[Dict[str, Any]] = []
    seen = set()
    for raw_model in raw_models:
        matches = find_matching_cars(raw_model, top_k=1)
        if matches:
            key = matches[0]["_display_name"]
            if key not in seen:
                selected.append(matches[0])
                seen.add(key)

    if len(selected) < 2:
        return "Cần ít nhất 2 mẫu xe hợp lệ để so sánh. Ví dụ: VF 5, VF 6, VF 7"

    headers = ["Mẫu xe", "Giá", "Số chỗ", "Tầm chạy", "Sạc nhanh 10-70%", "Loại xe"]
    widths = [18, 18, 10, 14, 18, 22]
    divider = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
    lines = [divider, "-" * len(divider)]
    for car in selected[:4]:
        row = [
            car["_display_name"][:18],
            vn_money_million(car.get("price_million"))[:18],
            str(first_non_empty(car.get("seats"), "?"))[:10],
            f"{first_non_empty(car.get('range_km_per_full_charge'), '?')} km"[:14],
            f"{first_non_empty(car.get('charge_time_min'), '?')} phút"[:18],
            str(car.get("type", "chưa rõ"))[:22],
        ]
        lines.append(" | ".join(value.ljust(w) for value, w in zip(row, widths)))

    lines.append("")
    best_price = min((c for c in selected if c.get("price_million") is not None), key=lambda x: x["price_million"], default=None)
    best_range = max(selected, key=lambda x: safe_float(x.get("range_km_per_full_charge"), 0), default=None)
    if best_price:
        lines.append(f"- Dễ tiếp cận nhất về giá: {best_price['_display_name']} ({vn_money_million(best_price.get('price_million'))})")
    if best_range:
        lines.append(
            f"- Tầm chạy nổi bật nhất: {best_range['_display_name']} ({best_range.get('range_km_per_full_charge')} km/lần sạc)"
        )
    return "\n".join(lines)


@tool("vinfast_warranty_policy")
def vinfast_warranty_policy(question: str) -> str:
    """Tra cứu chính sách bảo hành VinFast, ưu tiên trang chính thức và kết hợp data nội bộ khi có mẫu xe cụ thể."""
    lines = [
        f"Nguồn chính thức ưu tiên: {VINFAST_WARRANTY_URL}",
        f"Nguồn chính sách tổng hợp: {VINFAST_POLICY_URL}",
    ]

    model_matches = find_matching_cars(question, top_k=1)
    if model_matches:
        car = model_matches[0]
        maint = maintenance_for_car(car)
        if maint:
            vehicle = maint.get("warranty", {}).get("vehicle", {}).get("personal_use", {})
            battery = maint.get("warranty", {}).get("battery", {}).get("personal_use", {})
            lines.append(f"Mẫu xe nội bộ khớp nhất: {car['_display_name']}")
            lines.append(
                "Bảo hành trong data nhóm: "
                f"xe={vehicle.get('duration', 'chưa rõ')} | "
                f"pin={battery.get('duration', 'chưa rõ')} | "
                f"cam kết dung lượng pin={maint.get('warranty', {}).get('battery', {}).get('capacity_commitment', 'chưa rõ')}"
            )
            exclusions = maint.get("exclusions", [])
            if exclusions:
                lines.append(f"Một số loại trừ trong data: {'; '.join(exclusions[:5])}")

    official_text = fetch_clean_text(VINFAST_WARRANTY_URL, max_chars=4500)
    lines.append("Tóm lược text từ trang bảo hành chính thức (rút gọn):")
    lines.append(official_text)

    search_results = web_search(f"site:vinfastauto.com VinFast bảo hành {question}", max_results=4)
    if search_results:
        lines.append("Kết quả web hỗ trợ:")
        for idx, item in enumerate(search_results, start=1):
            lines.append(f"{idx}. {item['title']} | {item['url']} | {item['snippet']}")

    lines.append(f"Hotline tham khảo: {VINFAST_HOTLINE}")
    return "\n".join(lines).strip()


@tool("vinfast_showroom_stock_search")
def vinfast_showroom_stock_search(location: str, model: str = "") -> str:
    """Tìm showroom/đại lý VinFast gần khu vực quan tâm và dò tín hiệu tồn xe trên web. Đây là tìm kiếm best-effort, không phải API tồn kho thời gian thực."""
    query_parts = ["VinFast", location.strip()]
    if model.strip():
        query_parts.append(model.strip())
    query_parts.extend(["showroom", "con xe", "giao ngay"])
    query = " ".join(part for part in query_parts if part)

    lines = [
        f"Trang showroom chính thức: {VINFAST_SHOWROOM_URL}",
        f"Trang mua xe chính thức: {VINFAST_DEPOSIT_LIST_URL}",
        "Lưu ý: VinFast không công khai công cụ tồn kho realtime ở trang public, nên kết quả dưới đây chỉ là lead để sales kiểm tra thêm.",
    ]

    official_results = web_search(f"site:vinfastauto.com VinFast showroom {location}", max_results=3)
    dealer_results = web_search(query, max_results=6)

    if official_results:
        lines.append("Nguồn chính thức nên mở trước:")
        for idx, item in enumerate(official_results, start=1):
            lines.append(f"{idx}. {item['title']} | {item['url']} | {item['snippet']}")

    if dealer_results:
        lines.append("Kết quả dò tồn xe / giao ngay / showroom gần đúng:")
        for idx, item in enumerate(dealer_results, start=1):
            lines.append(f"{idx}. {item['title']} | {item['url']} | {item['snippet']}")
    else:
        lines.append("Chưa lấy được kết quả web. Hãy dùng trực tiếp trang showroom chính thức hoặc gọi hotline để xác minh tồn xe.")

    if model.strip():
        official_model_url = official_url_for_model(model)
        if official_model_url:
            lines.append(f"Link mẫu xe chính thức để đăng ký tư vấn: {official_model_url}")

    lines.append(f"Hotline xác minh tồn xe/giao xe: {VINFAST_HOTLINE}")
    return "\n".join(lines).strip()


@tool("save_showroom_appointment")
def save_showroom_appointment(full_name: str, phone: str, showroom: str, appointment_datetime: str) -> str:
    """Lưu lịch hẹn showroom khi đã có đủ 4 trường bắt buộc: họ tên, số điện thoại, showroom, ngày giờ."""
    full_name = compact_whitespace(full_name)
    phone = compact_whitespace(phone)
    showroom = compact_whitespace(showroom)
    appointment_datetime = compact_whitespace(appointment_datetime)

    if not full_name:
        return "Thiếu họ tên khách hàng, chưa thể lưu lịch hẹn."
    if not phone:
        return "Thiếu số điện thoại, chưa thể lưu lịch hẹn."
    if not showroom:
        return "Thiếu tên showroom, chưa thể lưu lịch hẹn."
    if not appointment_datetime:
        return "Thiếu ngày giờ hẹn, chưa thể lưu lịch hẹn."
    if not is_valid_phone(phone):
        return "Số điện thoại chưa đúng định dạng Việt Nam, vui lòng nhập lại 10-11 số."

    ensure_booking_dir()
    now = datetime.now()
    safe_name = slugify_filename(full_name)
    safe_phone = normalize_phone(phone)
    file_name = f"{now.strftime('%Y%m%d_%H%M%S')}_{safe_name}_{safe_phone[-4:]}.json"
    file_path = BOOKING_DIR / file_name

    payload = {
        "ho_ten": full_name,
        "so_dien_thoai": safe_phone,
        "showroom": showroom,
        "ngay_gio": appointment_datetime,
        "submitted_at": now.isoformat(timespec="seconds"),
        "source": "HungAgent",
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return (
        "Đã lưu lịch hẹn thành công. "
        f"File JSON: {file_path} | "
        f"Khách: {full_name} | SĐT: {safe_phone} | Showroom: {showroom} | Ngày giờ: {appointment_datetime}"
    )


TOOLS = [
    vinfast_recommendation,
    vinfast_specs_lookup,
    vinfast_compare,
    vinfast_warranty_policy,
    vinfast_showroom_stock_search,
    save_showroom_appointment,
]

SYSTEM_PROMPT = """
Bạn là Vinicius Chat - tư vấn viên VinFast chạy bằng LangChain + LangGraph cho hackathon.

Nguyên tắc trả lời:
1. Luôn trả lời bằng tiếng Việt, rõ ràng, có cấu trúc.
2. Khi user hỏi mẫu xe phù hợp => ưu tiên dùng vinfast_recommendation.
3. Khi user hỏi thông số, phiên bản, so sánh xe => dùng vinfast_specs_lookup hoặc vinfast_compare.
4. Khi user hỏi bảo hành/chính sách mới nhất => dùng vinfast_warranty_policy.
5. Khi user hỏi showroom nào còn xe / giao ngay => bắt buộc dùng vinfast_showroom_stock_search và nói rõ đây là best-effort, chưa phải xác nhận tồn kho realtime.
6. Khi user muốn đặt lịch xem xe, đặt lịch tới showroom, đặt lịch tư vấn hoặc lái thử:
   - Bắt buộc thu thập đủ 4 trường: Họ tên, SĐT, Showroom, Ngày giờ.
   - Nếu thiếu trường nào thì chỉ hỏi đúng phần còn thiếu, ngắn gọn, lịch sự.
   - Chỉ khi đã có đủ 4 trường thì mới gọi tool save_showroom_appointment.
   - Sau khi lưu thành công, cảm ơn khách và xác nhận lại 4 thông tin vừa lưu.
7. Phân biệt rõ:
   - Fact từ data local của nhóm.
   - Fact từ website chính thức VinFast.
   - Tín hiệu web/bên thứ ba chỉ để tham khảo.
8. Không bịa chính sách, không bịa tồn kho, không bịa lịch đã đặt. Nếu chưa đủ chắc chắn thì nói mức độ chắc chắn.
9. Nếu người dùng mới chỉ nói "tôi muốn đặt lịch" mà chưa có đủ thông tin, hãy chủ động hỏi theo form này:
   - Họ tên:
   - SĐT:
   - Showroom muốn đến:
   - Ngày giờ mong muốn:
10. Kết thúc nên có gợi ý bước tiếp theo thực dụng như: so sánh 2 mẫu, tính ngân sách, để lại thông tin, gọi showroom.
""".strip()


def build_agent(model_name: Optional[str] = None):
    model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    llm = ChatOpenAI(model=model_name, temperature=0.2)
    llm_with_tools = llm.bind_tools(TOOLS)

    def call_model(state: MessagesState):
        response = llm_with_tools.invoke([SystemMessage(content=SYSTEM_PROMPT)] + state["messages"])
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("agent", call_model)
    builder.add_node("tools", ToolNode(TOOLS))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        tools_condition,
        {
            "tools": "tools",
            END: END,
        },
    )
    builder.add_edge("tools", "agent")
    return builder.compile(checkpointer=MemorySaver())


def chat_cli() -> None:
    load_dotenv(BASE_DIR / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Thiếu OPENAI_API_KEY trong file .env")

    ensure_booking_dir()
    graph = build_agent()
    config = {"configurable": {"thread_id": "vinfast-hackathon-cli"}}

    print("HungAgent VinFast (LangChain + LangGraph)")
    print("Gõ 'exit' để thoát.")
    print("Ví dụ:")
    print("- Tôi có 800 triệu, gia đình 4 người, đi nội thành và chưa có chỗ sạc")
    print("- So sánh VF 5, VF 6, VF 7")
    print("- Chính sách bảo hành pin VF 8 hiện tại là gì?")
    print("- Ở Hà Nội showroom nào còn VF 7 giao sớm?")
    print("- Tôi muốn đặt lịch xem xe VF 6 ở showroom VinFast Phạm Văn Đồng vào 15h thứ Bảy")

    while True:
        user_text = input("\nBạn: ").strip()
        if not user_text:
            continue
        if user_text.lower() in {"exit", "quit"}:
            print("Tạm biệt.")
            break

        result = graph.invoke({"messages": [HumanMessage(content=user_text)]}, config=config)
        final_message = result["messages"][-1]
        print("\nHungAgent:")
        print(final_message.content)


if __name__ == "__main__":
    chat_cli()
