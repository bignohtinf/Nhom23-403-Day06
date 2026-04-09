"""
VinFast AI Chatbot — tư vấn mua xe, bảo dưỡng, phân tích review
Architecture: LangGraph agent loop  START → agent ↔ tools → END

Workflow dữ liệu:
  1. Truy xuất JSON từ folder data/ trước
  2. Nếu không tìm thấy hoặc thiếu thông tin → gọi LLM làm giàu ngữ nghĩa
  3. Tìm showroom → dùng DuckDuckGo web search (thời gian thực)
"""

import json
import os
import random
import re
import string
import unicodedata
from datetime import datetime
from typing import Annotated, Dict, List, Optional, TypedDict

import requests
from bs4 import BeautifulSoup

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()

# ── Đường dẫn dữ liệu & log ──────────────────────────────────────────────
DATA_DIR = r"C:\Users\Admin\Desktop\AI Thực Chiến\BuiDucTien-day6\Nhom23-403-Day06\data"
LOG_DIR  = r"C:\Users\Admin\Desktop\AI Thực Chiến\BuiDucTien-day6\Nhom23-403-Day06\log"
os.makedirs(LOG_DIR, exist_ok=True)

with open(os.path.join(DATA_DIR, "cars.json"), encoding="utf-8") as f:
    CARS = json.load(f)

with open(os.path.join(DATA_DIR, "maintenance.json"), encoding="utf-8") as f:
    MAINTENANCE = json.load(f)

with open(os.path.join(DATA_DIR, "reviews_processed.json"), encoding="utf-8") as f:
    REVIEWS = json.load(f)

# ── Model & API keys từ .env ──────────────────────────────────────────────
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
SERPAPI_KEY    = os.getenv("SERPAPI_KEY", "")
SERPAPI_URL    = "https://serpapi.com/search.json"
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# ── HTTP constants ────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 20

# ── VinFast official URLs ─────────────────────────────────────────────────
VINFAST_SHOWROOM_URL    = "https://vinfastauto.com/vn_vi/tim-kiem-showroom-tram-sac"
VINFAST_DEPOSIT_LIST_URL = "https://shop.vinfastauto.com/vn_vi/dat-coc-o-to-dien-vinfast.html"
VINFAST_HOTLINE         = "1900 23 23 89"

OFFICIAL_MODEL_URLS: Dict[str, str] = {
    "vf 3":       "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-vf3.html",
    "vf3":        "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-vf3.html",
    "vf 5":       "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-dien-vf5.html",
    "vf5":        "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-dien-vf5.html",
    "vf 6":       "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-dien-vf6.html",
    "vf6":        "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-dien-vf6.html",
    "vf 7":       "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-dien-vf7.html",
    "vf7":        "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-dien-vf7.html",
    "vf 8":       "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-vf8.html",
    "vf8":        "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-vf8.html",
    "vf 9":       "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-vf9.html",
    "vf9":        "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-vf9.html",
    "limo green": "https://vinfastauto.com/vn_vi/limo-green",
    "ec van":     "https://shop.vinfastauto.com/vn_vi/vinfast-ecvan.html",
}


def _normalize_text(text: str) -> str:
    """Bỏ dấu, lowercase, loại ký tự đặc biệt — dùng để so khớp model."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def official_url_for_model(text: str) -> Optional[str]:
    """Trả về link chính hãng VinFast cho model, hoặc None nếu không tìm thấy."""
    q = _normalize_text(text)
    if q in OFFICIAL_MODEL_URLS:
        return OFFICIAL_MODEL_URLS[q]
    for key, url in OFFICIAL_MODEL_URLS.items():
        if key in q or q in key:
            return url
    return None


# ── Helper: Làm giàu ngữ nghĩa với LLM khi dữ liệu JSON không đủ ─────────
_enrich_llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0.3)


def _enrich_with_llm(query: str, partial_data: str = "") -> str:
    """Gọi LLM bổ sung thông tin khi dữ liệu JSON không tìm thấy hoặc thiếu."""
    if partial_data:
        prompt = (
            "Bạn là chuyên gia tư vấn xe VinFast.\n"
            f"Dữ liệu tìm được từ hệ thống (có thể thiếu):\n{partial_data}\n\n"
            f"Ngữ cảnh / câu hỏi: {query}\n\n"
            "Hãy bổ sung những thông tin còn thiếu hoặc làm rõ thêm. "
            "Phân biệt rõ ràng:\n"
            "  [Dữ liệu hệ thống] — thông tin lấy từ dữ liệu chính hãng\n"
            "  [Bổ sung từ AI] — kiến thức bổ sung, cần kiểm chứng với hãng"
        )
    else:
        prompt = (
            "Bạn là chuyên gia tư vấn xe VinFast.\n"
            f"Không tìm thấy dữ liệu trong hệ thống cho: {query}\n\n"
            "Hãy trả lời dựa trên kiến thức chung về VinFast. "
            "Bắt đầu phản hồi bằng dòng:\n"
            "  [Thông tin tham khảo từ AI — cần kiểm chứng với hãng chính thức]\n"
            "rồi mới đưa ra nội dung."
        )
    response = _enrich_llm.invoke([HumanMessage(content=prompt)])
    return response.content


# ── Helper: DuckDuckGo HTML scraping (requests + BeautifulSoup) ───────────
def ddg_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Scrape DuckDuckGo HTML interface — không cần API key."""
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results: List[Dict[str, str]] = []
        for item in soup.select(".result"):
            a_tag = item.select_one(".result__title a") or item.select_one("a.result__a")
            snippet = item.select_one(".result__snippet")
            if not a_tag:
                continue
            title = _compact(a_tag.get_text(" ", strip=True))
            href  = a_tag.get("href", "")
            body  = _compact(snippet.get_text(" ", strip=True) if snippet else "")
            if title and href:
                results.append({"title": title, "url": href, "snippet": body})
            if len(results) >= max_results:
                break
        return results
    except Exception:
        return []


# ── Helper: Web search — Tavily → SerpAPI → DuckDuckGo fallback ───────────
def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Ưu tiên:
      1. Tavily API  (nếu TAVILY_API_KEY có giá trị)
      2. SerpAPI     (nếu SERPAPI_KEY có giá trị)
      3. DuckDuckGo  (HTML scraping, không cần key)
    Trả về list[{title, url, snippet}].
    """
    # 1. Tavily
    if TAVILY_API_KEY:
        try:
            resp = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key":      TAVILY_API_KEY,
                    "query":        query,
                    "max_results":  max_results,
                    "search_depth": "basic",
                },
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            output = [
                {
                    "title":   item.get("title", ""),
                    "url":     item.get("url", ""),
                    "snippet": _compact(item.get("content", "")),
                }
                for item in data.get("results", [])[:max_results]
            ]
            if output:
                return output
        except Exception:
            pass

    # 2. SerpAPI
    if SERPAPI_KEY:
        try:
            resp = requests.get(
                SERPAPI_URL,
                params={
                    "engine": "google", "q": query,
                    "api_key": SERPAPI_KEY,
                    "location": "Vietnam", "hl": "vi", "gl": "vn",
                    "num": max_results,
                },
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            output = [
                {
                    "title":   item.get("title", ""),
                    "url":     item.get("link", ""),
                    "snippet": _compact(item.get("snippet", "")),
                }
                for item in data.get("organic_results", [])[:max_results]
            ]
            if output:
                return output
        except Exception:
            pass

    # 3. DuckDuckGo HTML scraping
    return ddg_search(query, max_results=max_results)


# ── Helper: Phân tích chuỗi ngày giờ tiếng Việt ──────────────────────────
_DATE_PATTERNS = [
    r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})\s+(?:lúc\s+)?(\d{1,2}):(\d{2})",  # dd/mm/yyyy lúc HH:MM
    r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",                                    # dd/mm/yyyy
]

def _parse_booking_date(date_str: str) -> datetime | None:
    """Chuyển chuỗi ngày giờ tiếng Việt sang datetime. Trả về None nếu không parse được."""
    s = date_str.strip()
    for pattern in _DATE_PATTERNS:
        m = re.search(pattern, s)
        if m:
            groups = m.groups()
            day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
            hour = int(groups[3]) if len(groups) > 3 and groups[3] else 9
            minute = int(groups[4]) if len(groups) > 4 and groups[4] else 0
            try:
                return datetime(year, month, day, hour, minute)
            except ValueError:
                return None
    return None


# ── Helper: Validate thông tin đặt lịch ──────────────────────────────────
BUSINESS_HOUR_START = 8   # 08:00
BUSINESS_HOUR_END   = 17  # 17:00
MAX_DAYS_AHEAD      = 60  # không đặt quá 60 ngày từ hôm nay
WEEKDAY_NAMES = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]

def _validate_booking(customer_name: str, phone: str, preferred_date: str) -> list[str]:
    """
    Kiểm tra các ràng buộc đặt lịch. Trả về list lỗi (rỗng = hợp lệ).
    Các trường hợp ngoại lệ:
      - Tên trống
      - SĐT không hợp lệ (không phải 10 số, không bắt đầu bằng 0)
      - Ngày không parse được
      - Ngày trong quá khứ
      - Ngày quá xa (> 60 ngày)
      - Chủ Nhật (showroom đóng cửa)
      - Ngoài giờ làm việc (trước 08:00 hoặc sau 17:00)
    """
    errors: list[str] = []

    # 1. Tên không được trống
    if not customer_name.strip():
        errors.append("Tên khách hàng không được để trống.")

    # 2. Số điện thoại: 10 chữ số, bắt đầu bằng 0
    phone_digits = re.sub(r"\D", "", phone)
    if len(phone_digits) != 10:
        errors.append(f"Số điện thoại '{phone}' không hợp lệ — cần đúng 10 chữ số.")
    elif not phone_digits.startswith("0"):
        errors.append(f"Số điện thoại '{phone}' không hợp lệ — phải bắt đầu bằng 0.")

    # 3. Phân tích ngày giờ
    dt = _parse_booking_date(preferred_date)
    if dt is None:
        errors.append(
            f"Không nhận dạng được ngày '{preferred_date}'. "
            "Dùng định dạng: dd/mm/yyyy lúc HH:MM (VD: 20/04/2025 lúc 09:00)."
        )
    else:
        now = datetime.now()

        # 4. Ngày phải trong tương lai
        if dt <= now:
            errors.append(
                f"Ngày đặt lịch '{preferred_date}' đã qua. "
                f"Vui lòng chọn ngày sau {now.strftime('%d/%m/%Y %H:%M')}."
            )

        # 5. Không đặt quá 60 ngày tới
        elif (dt - now).days > MAX_DAYS_AHEAD:
            errors.append(
                f"Ngày đặt lịch quá xa (hơn {MAX_DAYS_AHEAD} ngày). "
                "Vui lòng đặt trong vòng 60 ngày tới."
            )

        # 6. Không đặt Chủ Nhật (weekday() == 6)
        if dt.weekday() == 6:
            errors.append(
                f"Showroom VinFast không hoạt động vào Chủ Nhật. "
                "Vui lòng chọn ngày Thứ Hai đến Thứ Bảy."
            )

        # 7. Trong giờ làm việc
        if not (BUSINESS_HOUR_START <= dt.hour < BUSINESS_HOUR_END):
            errors.append(
                f"Giờ hẹn {dt.hour:02d}:{dt.minute:02d} ngoài giờ làm việc. "
                f"Vui lòng chọn từ {BUSINESS_HOUR_START:02d}:00 đến {BUSINESS_HOUR_END:02d}:00."
            )

    return errors


# ── Helper: Lưu thông tin đặt lịch vào file JSON trong LOG_DIR ────────────
def _save_booking_log(booking_data: dict) -> str:
    """
    Lưu booking thành 2 nơi:
      1. File riêng: log/<booking_id>_<timestamp>.json
      2. File tổng: log/bookings_all.json  (append vào list)
    Trả về đường dẫn file riêng đã lưu.
    """
    booking_id = booking_data.get("booking_id", "UNKNOWN")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. File riêng
    single_path = os.path.join(LOG_DIR, f"{booking_id}_{ts}.json")
    with open(single_path, "w", encoding="utf-8") as f:
        json.dump(booking_data, f, ensure_ascii=False, indent=2)

    # 2. File tổng — đọc list cũ (nếu có), append, ghi lại
    all_path = os.path.join(LOG_DIR, "bookings_all.json")
    try:
        with open(all_path, "r", encoding="utf-8") as f:
            all_bookings: list = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        all_bookings = []

    all_bookings.append(booking_data)
    with open(all_path, "w", encoding="utf-8") as f:
        json.dump(all_bookings, f, ensure_ascii=False, indent=2)

    return single_path


# ── TOOL 1: Truy vấn xe ───────────────────────────────────────────────────
@tool
def query_cars(
    budget_max_million: Optional[float] = None,
    seats_min: Optional[int] = None,
    range_km_min: Optional[int] = None,
    model_name: Optional[str] = None,
) -> str:
    """
    Truy vấn danh mục xe VinFast từ dữ liệu chính hãng (data/cars.json).
    Lọc theo: ngân sách tối đa (triệu đồng), số chỗ tối thiểu,
    quãng đường tối thiểu mỗi lần sạc (km), hoặc tên model cụ thể.
    Nếu không tìm thấy → gọi LLM làm giàu ngữ nghĩa.
    """
    results = CARS[:]

    if model_name:
        kw = model_name.lower()
        results = [
            c for c in results
            if kw in c["model"].lower() or kw in c.get("model_version", "").lower()
        ]
    if budget_max_million is not None:
        results = [c for c in results if c.get("price_million") and c["price_million"] <= budget_max_million]
    if seats_min is not None:
        results = [c for c in results if c.get("seats") and c["seats"] >= seats_min]
    if range_km_min is not None:
        results = [
            c for c in results
            if c.get("range_km_per_full_charge") and c["range_km_per_full_charge"] >= range_km_min
        ]

    # Không tìm thấy → LLM fallback
    if not results:
        criteria_desc = []
        if model_name:
            criteria_desc.append(f"model '{model_name}'")
        if budget_max_million is not None:
            criteria_desc.append(f"ngân sách ≤{budget_max_million} triệu")
        if seats_min is not None:
            criteria_desc.append(f"≥{seats_min} chỗ")
        if range_km_min is not None:
            criteria_desc.append(f"quãng đường ≥{range_km_min} km")
        query_desc = "xe VinFast phù hợp với tiêu chí: " + ", ".join(criteria_desc)
        return _enrich_with_llm(query_desc)

    lines = ["[Nguồn: Dữ liệu chính hãng VinFast — data/cars.json]\n"]
    shown = results[:6]
    for c in shown:
        version = f" {c['model_version']}" if c.get("model_version") else ""
        price = f"{c['price_million']:,.0f} triệu" if c.get("price_million") else "Chưa công bố giá"
        seats = f"{c['seats']} chỗ" if c.get("seats") else "—"
        rng = f"{c['range_km_per_full_charge']} km"
        chg = f"sạc {c['charge_time_min']} phút"
        sz = c.get("size_mm", {})
        dim = f"{sz.get('length')}×{sz.get('width')}×{sz.get('height')} mm" if sz else "—"
        colors = c.get("color", [])
        color_str = ", ".join(colors[:3]) + ("..." if len(colors) > 3 else "")
        lines.append(
            f"• {c['model']}{version}\n"
            f"  Giá: {price} | Chỗ: {seats} | Quãng đường: {rng}/lần sạc | {chg}\n"
            f"  Kích thước: {dim}\n"
            f"  Màu: {color_str}"
        )

    # ── Tìm showroom + link chính hãng (Tavily → SerpAPI → DDG scraping) ──
    unique_models = list({c["model"] for c in shown})
    query_models  = " ".join(unique_models[:2])
    showroom_lines = ["\n[Showroom & Link mua xe — nguồn web, cần xác nhận trực tiếp]"]

    # Link chính hãng từ OFFICIAL_MODEL_URLS
    official_links_added: set[str] = set()
    for m in unique_models[:3]:
        link = official_url_for_model(m)
        if link and link not in official_links_added:
            official_links_added.add(link)
            showroom_lines.append(f"  ★ [Chính hãng] {m}: {link}")

    showroom_lines.append(f"  ★ Tìm showroom: {VINFAST_SHOWROOM_URL}")

    # Kết quả web (official site trước, dealer sau)
    try:
        official_results = web_search(
            f"site:vinfastauto.com VinFast showroom {query_models}",
            max_results=3,
        )
        dealer_results = web_search(
            f"showroom đại lý VinFast {query_models} mua xe giao ngay",
            max_results=4,
        )
        seen_urls: set[str] = set()
        for r in official_results + dealer_results:
            url  = r.get("url") or r.get("href", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            snip = r.get("snippet") or r.get("body", "")
            showroom_lines.append(
                f"  • {r['title']}\n    {_compact(snip)[:130]}\n    {url}"
            )
    except Exception as e:
        showroom_lines.append(f"  Không tìm được tự động ({e}).")

    showroom_lines.append(f"  Hotline xác minh: {VINFAST_HOTLINE}")
    lines.append("\n".join(showroom_lines))
    return "\n\n".join(lines)


# ── TOOL 2: Bảo dưỡng & bảo hành ─────────────────────────────────────────
@tool
def query_maintenance(model_name: str) -> str:
    """
    Tra cứu thông tin bảo dưỡng định kỳ, thời hạn bảo hành xe và pin,
    dịch vụ hậu mãi, các trường hợp loại trừ bảo hành, và hotline hỗ trợ
    từ data/maintenance.json. Nếu thiếu trường → LLM bổ sung.
    """
    kw = model_name.lower()
    matched = None
    for entry in MAINTENANCE:
        models = entry.get("model", [])
        if isinstance(models, str):
            models = [models]
        if any(kw in m.lower() for m in models):
            matched = entry
            break

    # Không tìm thấy → LLM fallback
    if not matched:
        return _enrich_with_llm(f"thông tin bảo dưỡng và bảo hành xe VinFast {model_name}")

    out = ["[Nguồn: Tài liệu bảo hành chính hãng VinFast — data/maintenance.json]\n"]
    model_label = ", ".join(matched["model"]) if isinstance(matched["model"], list) else matched["model"]
    out.append(f"Model: {model_label}\n")

    w = matched.get("warranty", {})
    v = w.get("vehicle", {})
    if v.get("personal_use"):
        out.append(f"Bảo hành xe (sử dụng cá nhân): {v['personal_use']['duration']}")
    if v.get("commercial_use"):
        out.append(f"Bảo hành xe (thương mại): {v['commercial_use']['duration']}")
    if v.get("standard"):
        out.append(f"Bảo hành xe: {v['standard']['duration']}")

    b = w.get("battery", {})
    ib = b.get("included_battery") or b.get("personal_use") or {}
    dur = ib.get("duration") or (ib.get("standard", {}).get("duration") if isinstance(ib, dict) else None)
    if dur:
        out.append(f"Bảo hành pin: {dur} (dung lượng tối thiểu ≥70%)")

    cond = matched.get("maintenance", {}).get("condition", [])
    if cond:
        out.append("\nĐiều kiện để hưởng bảo hành:")
        for c in cond[:3]:
            out.append(f"  • {c}")

    excl = matched.get("exclusions", [])
    if excl:
        out.append("\nKhông bảo hành trong các trường hợp:")
        for e in excl[:4]:
            out.append(f"  • {e}")

    after = matched.get("after_sales", [])
    if after:
        out.append("\nDịch vụ hậu mãi:")
        for s in after:
            out.append(f"  • {s['service']}: {s['detail']}")

    hotline = matched.get("hotline")
    if hotline:
        if isinstance(hotline, list):
            hotline = " / ".join(h.get("number", "") for h in hotline)
        out.append(f"\nHotline hỗ trợ: {hotline}")

    # Kiểm tra các trường quan trọng còn thiếu → LLM bổ sung
    missing = []
    if not v.get("personal_use") and not v.get("standard"):
        missing.append("thời hạn bảo hành xe")
    if not dur:
        missing.append("bảo hành pin")
    if not excl:
        missing.append("các trường hợp loại trừ bảo hành")

    base_result = "\n".join(out)
    if missing:
        enriched = _enrich_with_llm(
            f"thông tin còn thiếu ({', '.join(missing)}) cho xe VinFast {model_name}",
            partial_data=base_result,
        )
        return base_result + "\n\n" + enriched

    return base_result


# ── TOOL 3: Tóm tắt review theo tiêu chí ─────────────────────────────────
@tool
def query_reviews(model_name: str) -> str:
    """
    Tóm tắt đánh giá cộng đồng (pros/cons) từ data/reviews_processed.json,
    phân loại theo tiêu chí: Hiệu năng, Tiện nghi, Chi phí.
    Nếu không có dữ liệu hoặc review quá ít → LLM bổ sung.
    """
    kw = model_name.lower().replace(" ", "")
    matched = None
    for r in REVIEWS:
        mk = r["model"].lower().replace(" ", "")
        if kw in mk or mk in kw:
            matched = r
            break

    # Không tìm thấy → LLM fallback
    if not matched:
        return _enrich_with_llm(
            f"đánh giá ưu/nhược điểm xe VinFast {model_name} theo tiêu chí Hiệu năng, Tiện nghi, Chi phí"
        )

    def tag(text: str) -> str:
        t = text.lower()
        if any(w in t for w in ["tăng tốc", "mạnh", "vọt", "bứt", "lanh", "êm", "motor", "động cơ", "dẫn động"]):
            return "[Hiệu năng]"
        if any(w in t for w in ["tiện nghi", "ghế", "loa", "màn hình", "nội thất", "không gian", "tính năng", "công nghệ"]):
            return "[Tiện nghi]"
        if any(w in t for w in ["chi phí", "giá", "sạc", "tiết kiệm", "rẻ", "bảo dưỡng", "ưu đãi"]):
            return "[Chi phí]"
        return "[Khác]"

    pros = matched.get("pros", [])
    cons = matched.get("cons", [])
    out = [
        "[Nguồn: Ý kiến cộng đồng — data/reviews_processed.json]\n",
        f"Xe: {matched['model']} — Tổng hợp review người dùng\n",
        "ƯU ĐIỂM:",
    ]
    for p in pros[:5]:
        out.append(f"  + {tag(p)} {p}")
    out.append("\nNHƯỢC ĐIỂM:")
    for c in cons[:5]:
        out.append(f"  - {tag(c)} {c}")

    base_result = "\n".join(out)

    # Dữ liệu review quá ít → LLM bổ sung
    if len(pros) < 3 or len(cons) < 3:
        enriched = _enrich_with_llm(
            f"đánh giá bổ sung về xe VinFast {model_name} theo tiêu chí Hiệu năng, Tiện nghi, Chi phí",
            partial_data=base_result,
        )
        return base_result + "\n\n" + enriched

    return base_result


# ── TOOL 4: Tìm kiếm web — giá, ưu đãi ───────────────────────────────────
@tool
def search_web(query: str) -> str:
    """
    Tìm kiếm web (DuckDuckGo) để lấy giá thực tế, ưu đãi/khuyến mãi hiện hành.
    Trả về kết quả kèm URL nguồn. Dùng khi cần giá hiện tại hoặc khuyến mãi.
    Ví dụ query: 'VF 7 giá tháng 4 2025', 'ưu đãi VinFast tháng này'.
    """
    try:
        results = web_search(f"VinFast {query}", max_results=4)
        if not results:
            return "Không tìm thấy kết quả. Thử từ khóa khác."

        lines = ["[Nguồn: Kết quả tìm kiếm web — cần kiểm chứng với tư vấn viên]\n"]
        for r in results:
            snippet = _compact(r.get("snippet") or r.get("body", ""))[:180]
            url = r.get("url") or r.get("href", "")
            lines.append(f"• {r['title']}\n  {snippet}...\n  URL: {url}")
        return "\n\n".join(lines)

    except ImportError:
        return (
            "Thư viện duckduckgo-search chưa được cài.\n"
            "Chạy: pip install duckduckgo-search"
        )
    except Exception as e:
        return f"Lỗi tìm kiếm: {e}"


# ── TOOL 5: Tìm showroom + đặt lịch ──────────────────────────────────────
@tool
def book_showroom(
    customer_name: str,
    phone: str,
    model_interest: str,
    preferred_date: str,
    showroom_city: str = "Hà Nội",
) -> str:
    """
    Tìm showroom VinFast gần nhất qua web search (thời gian thực),
    sau đó tạo lịch hẹn tư vấn.
    Cần cung cấp: tên khách hàng, số điện thoại, model xe quan tâm,
    ngày giờ mong muốn (VD: '15/04/2025 lúc 10:00'), thành phố.
    Trả về JSON với status, errors (nếu có), và booking details.
    """
    # Bước 1: Validate đầu vào
    errors = _validate_booking(customer_name, phone, preferred_date)
    if errors:
        return json.dumps(
            {"status": "error", "errors": errors, "booking": None},
            ensure_ascii=False, indent=2,
        )

    # Bước 2: Tìm showroom qua DuckDuckGo
    showroom_results = []
    try:
        raw = web_search(
            f"showroom đại lý VinFast {showroom_city} địa chỉ số điện thoại",
            max_results=3,
        )
        showroom_results = [
            {"title": r["title"], "snippet": _compact(r.get("snippet") or r.get("body", ""))[:200], "url": r.get("url") or r.get("href", "")}
            for r in raw
        ]
    except Exception:
        showroom_results = [{"title": "Tra cứu tại website chính hãng",
                             "snippet": "", "url": "https://vinfastauto.com/vn/dai-ly"}]

    # Bước 3: Tạo mã đặt lịch
    booking_id = "VF-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    booking_detail = {
        "booking_id": booking_id,
        "type": "showroom_consultation",
        "customer_name": customer_name,
        "phone": phone,
        "model_interest": model_interest,
        "preferred_date": preferred_date,
        "city": showroom_city,
        "registered_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "note": "Tư vấn viên sẽ gọi xác nhận trong vòng 30 phút. Hotline: 1900 23 23 89",
        "showroom_results": showroom_results,
    }
    saved_path = _save_booking_log(booking_detail)
    result = {
        "status": "success",
        "errors": [],
        "saved_log": saved_path,
        "booking": booking_detail,
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


# ── TOOL 6: Đặt lịch lái thử ─────────────────────────────────────────────
TEST_DRIVE_URL = "https://shop.vinfastauto.com/vn_vi/dang-ky-lai-thu.html"

@tool
def book_test_drive(
    customer_name: str,
    phone: str,
    model_interest: str,
    preferred_date: str,
    city: str = "Hà Nội",
) -> str:
    """
    Đặt lịch lái thử xe VinFast tại trang chính hãng.
    Tìm thông tin địa điểm lái thử qua web search rồi hướng dẫn đăng ký.
    Cần cung cấp: tên khách hàng, số điện thoại, model xe muốn lái thử,
    ngày giờ mong muốn (VD: '20/04/2025 lúc 09:00'), thành phố.
    Trả về JSON với status, errors (nếu có), và booking details kèm link đăng ký.
    """
    # Bước 1: Validate đầu vào
    errors = _validate_booking(customer_name, phone, preferred_date)
    if errors:
        return json.dumps(
            {"status": "error", "errors": errors, "booking": None},
            ensure_ascii=False, indent=2,
        )

    # Bước 2: Tìm địa điểm lái thử qua DuckDuckGo
    location_results = []
    try:
        raw = web_search(
            f"đăng ký lái thử VinFast {city} địa điểm showroom 2025",
            max_results=3,
        )
        location_results = [
            {"title": r["title"], "snippet": _compact(r.get("snippet") or r.get("body", ""))[:200], "url": r.get("url") or r.get("href", "")}
            for r in raw
        ]
    except Exception:
        location_results = [{"title": "Xem địa điểm tại trang chính hãng",
                              "snippet": "", "url": TEST_DRIVE_URL}]

    # Bước 3: Tạo mã tham chiếu
    ref_id = "TD-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    booking_detail = {
        "booking_id": ref_id,
        "type": "test_drive",
        "customer_name": customer_name,
        "phone": phone,
        "model_interest": model_interest,
        "preferred_date": preferred_date,
        "city": city,
        "registered_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "registration_url": TEST_DRIVE_URL,
        "note": f"Điền mã {ref_id} vào phần ghi chú khi đăng ký online. Hotline: 1900 23 23 89",
        "location_results": location_results,
    }
    saved_path = _save_booking_log(booking_detail)
    result = {
        "status": "success",
        "errors": [],
        "saved_log": saved_path,
        "booking": booking_detail,
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


# ── TOOL 7: Tính giá lăn bánh + chi phí sở hữu + phân tích tài chính ─────

# Thuế trước bạ theo tỉnh/thành (xe ≤9 chỗ, lần đầu đăng ký)
_REGISTRATION_TAX: dict[str, float] = {
    "hà nội": 0.12,
    "ha noi": 0.12,
    "tp.hcm": 0.10,
    "tp hcm": 0.10,
    "hồ chí minh": 0.10,
    "ho chi minh": 0.10,
    "sài gòn": 0.10,
    "đà nẵng": 0.10,
    "da nang": 0.10,
    "hải phòng": 0.10,
    "hai phong": 0.10,
    "cần thơ": 0.10,
    "can tho": 0.10,
}
_DEFAULT_TAX_RATE = 0.10  # hầu hết các tỉnh còn lại

# Phí cố định (triệu đồng)
_LICENSE_PLATE_FEE  = 0.5    # phí cấp biển số
_ROAD_TAX_YEAR      = 3.6    # phí đường bộ năm đầu (xe ≤6 chỗ)
_MANDATORY_INS_YEAR = 0.5    # bảo hiểm TNDS bắt buộc / năm
_FIRST_INSPECTION   = 0.6    # phí đăng kiểm lần đầu

# Chi phí vận hành hằng tháng (ước tính)
_ELECTRICITY_VND_PER_KWH = 3_000   # 3.000 đ/kWh
_KWH_PER_100KM           = 15      # tiêu hao trung bình xe điện VinFast
_MAINTENANCE_YEAR        = 3.0     # bảo dưỡng định kỳ / năm (triệu)
_COMPREHENSIVE_INS_RATE  = 0.008   # bảo hiểm thân xe ~0.8% giá xe / năm
_PARKING_CITY_MONTH      = 1.5     # gửi xe tháng (ước tính nội thành)

# Tham số trả góp
_FINANCING_RATE_YEAR  = 0.10  # lãi suất 10%/năm
_FINANCING_MONTHS     = 60    # 5 năm
_DOWN_PAYMENT_RATIO   = 0.30  # đặt cọc 30%

# Ngưỡng đánh giá tỷ lệ chi phí / lương
_THRESH_GOOD   = 0.20   # ≤20% → Phù hợp
_THRESH_CAUTION= 0.30   # 20-30% → Cần cân nhắc
                         # >30% → Áp lực tài chính


def _monthly_payment(principal: float, rate_year: float, months: int) -> float:
    """Tính tiền trả góp mỗi tháng theo công thức anuity."""
    r = rate_year / 12
    return principal * r * (1 + r) ** months / ((1 + r) ** months - 1)


def _verdict(ratio: float) -> str:
    if ratio <= _THRESH_GOOD:
        return "Phù hợp"
    if ratio <= _THRESH_CAUTION:
        return "Cần cân nhắc"
    return "Áp lực tài chính cao"


@tool
def calculate_ownership_cost(
    model_name: str,
    province: str,
    monthly_salary_million: float,
    daily_km: float = 30.0,
    parking_fee_million: float = _PARKING_CITY_MONTH,
) -> str:
    """
    Tính toàn bộ chi phí sở hữu xe VinFast:
      1. Giá lăn bánh (giá xe + thuế trước bạ + phí đăng ký) theo tỉnh/thành.
      2. Chi phí vận hành hằng tháng (điện, bảo dưỡng, bảo hiểm, gửi xe).
      3. Phân tích độ phù hợp với mức lương user đặt ra (mua thẳng và trả góp 5 năm).
    Trả về JSON chi tiết từng khoản.
    Input:
      - model_name: tên model xe (VD: 'VF 7 Plus')
      - province: tỉnh/thành phố đăng ký xe
      - monthly_salary_million: lương tháng (triệu đồng)
      - daily_km: quãng đường di chuyển mỗi ngày (km, mặc định 30)
      - parking_fee_million: phí gửi xe tháng ước tính (triệu, mặc định 1.5)
    """
    # ── 1. Tìm giá xe từ cars.json ────────────────────────────────────────
    kw = model_name.lower()
    car = next(
        (c for c in CARS
         if kw in c["model"].lower() or kw in c.get("model_version", "").lower()),
        None,
    )

    if car is None:
        # Không có trong JSON → LLM ước tính
        llm_note = _enrich_with_llm(f"giá xe VinFast {model_name} và chi phí lăn bánh ước tính")
        return json.dumps(
            {"status": "not_found", "note": llm_note, "data": None},
            ensure_ascii=False, indent=2,
        )

    car_price: float = car.get("price_million", 0) or 0
    if car_price == 0:
        return json.dumps(
            {"status": "no_price", "note": f"Chưa có giá niêm yết cho {car['model']}.", "data": None},
            ensure_ascii=False, indent=2,
        )

    range_km: int = car.get("range_km_per_full_charge", 0)

    # ── 2. Tính giá lăn bánh ──────────────────────────────────────────────
    province_key = province.lower().strip()
    tax_rate = _REGISTRATION_TAX.get(province_key, _DEFAULT_TAX_RATE)
    reg_tax   = round(car_price * tax_rate, 2)
    road_tax  = _ROAD_TAX_YEAR
    total_on_road = round(
        car_price + reg_tax + _LICENSE_PLATE_FEE + road_tax
        + _MANDATORY_INS_YEAR + _FIRST_INSPECTION,
        2,
    )

    on_road_cost = {
        "car_price_million":           car_price,
        "registration_tax": {
            "rate_pct":        round(tax_rate * 100, 1),
            "amount_million":  reg_tax,
            "province":        province,
            "note":            "VinFast EV có thể được miễn/giảm — kiểm tra tại vinfastauto.com",
        },
        "license_plate_fee_million":   _LICENSE_PLATE_FEE,
        "road_tax_year1_million":      road_tax,
        "mandatory_insurance_million": _MANDATORY_INS_YEAR,
        "first_inspection_million":    _FIRST_INSPECTION,
        "total_on_road_million":       total_on_road,
    }

    # ── 3. Chi phí vận hành hằng tháng ────────────────────────────────────
    monthly_km        = daily_km * 30
    elec_kwh          = monthly_km / 100 * _KWH_PER_100KM
    elec_cost         = round(elec_kwh * _ELECTRICITY_VND_PER_KWH / 1_000_000, 3)
    road_tax_mo       = round(_ROAD_TAX_YEAR / 12, 3)
    mandatory_ins_mo  = round(_MANDATORY_INS_YEAR / 12, 3)
    comp_ins_mo       = round(car_price * _COMPREHENSIVE_INS_RATE / 12, 3)
    maintenance_mo    = round(_MAINTENANCE_YEAR / 12, 3)
    total_operating   = round(
        elec_cost + road_tax_mo + mandatory_ins_mo
        + comp_ins_mo + maintenance_mo + parking_fee_million,
        3,
    )

    monthly_op = {
        "daily_km":                          daily_km,
        "monthly_km":                        monthly_km,
        "electricity": {
            "kwh_per_100km":                 _KWH_PER_100KM,
            "price_vnd_per_kwh":             _ELECTRICITY_VND_PER_KWH,
            "monthly_kwh":                   round(elec_kwh, 1),
            "cost_million":                  elec_cost,
        },
        "road_tax_monthly_million":          road_tax_mo,
        "mandatory_insurance_monthly_million": mandatory_ins_mo,
        "comprehensive_insurance_monthly_million": comp_ins_mo,
        "maintenance_monthly_million":       maintenance_mo,
        "parking_monthly_million":           parking_fee_million,
        "total_monthly_million":             total_operating,
    }

    # ── 4. Phân tích tài chính theo lương ─────────────────────────────────
    annual_salary = monthly_salary_million * 12

    # Kịch bản mua thẳng
    op_ratio_cash  = total_operating / monthly_salary_million
    cash_scenario  = {
        "total_upfront_million":        total_on_road,
        "car_price_vs_annual_salary":   f"{round(car_price / annual_salary, 2)} năm lương",
        "monthly_operating_million":    total_operating,
        "operating_to_salary_pct":      f"{round(op_ratio_cash * 100, 1)}%",
        "verdict":                      _verdict(op_ratio_cash),
        "detail": (
            f"Chi phí vận hành tháng chiếm {round(op_ratio_cash * 100, 1)}% lương. "
            + ("Tài chính lành mạnh." if op_ratio_cash <= _THRESH_GOOD
               else "Nên lập quỹ dự phòng." if op_ratio_cash <= _THRESH_CAUTION
               else "Cân nhắc chọn mẫu xe phù hợp hơn.")
        ),
    }

    # Kịch bản trả góp 60 tháng, lãi 10%/năm, đặt cọc 30%
    down_payment    = round(car_price * _DOWN_PAYMENT_RATIO, 2)
    loan_amount     = round(car_price - down_payment, 2)
    installment_mo  = round(_monthly_payment(loan_amount, _FINANCING_RATE_YEAR, _FINANCING_MONTHS), 3)
    total_burden_mo = round(installment_mo + total_operating, 3)
    burden_ratio    = total_burden_mo / monthly_salary_million
    fin_scenario    = {
        "down_payment_30pct_million":   down_payment,
        "loan_amount_million":          loan_amount,
        "interest_rate_pct_year":       round(_FINANCING_RATE_YEAR * 100, 1),
        "term_months":                  _FINANCING_MONTHS,
        "monthly_installment_million":  installment_mo,
        "total_monthly_burden_million": total_burden_mo,
        "burden_to_salary_pct":         f"{round(burden_ratio * 100, 1)}%",
        "verdict":                      _verdict(burden_ratio),
        "detail": (
            f"Trả góp + vận hành = {total_burden_mo:.2f} triệu/tháng "
            f"({round(burden_ratio * 100, 1)}% lương). "
            + ("Hoàn toàn phù hợp." if burden_ratio <= _THRESH_GOOD
               else "Cần tiết kiệm thêm." if burden_ratio <= _THRESH_CAUTION
               else "Gánh nặng cao — nên chọn kỳ hạn dài hơn hoặc tăng đặt cọc.")
        ),
    }

    # Gợi ý tổng thể
    best_ratio = min(op_ratio_cash, burden_ratio)
    if best_ratio <= _THRESH_GOOD:
        overall = (f"Xe {car['model']} phù hợp với mức lương {monthly_salary_million} triệu. "
                   "Có thể cân nhắc mua thẳng hoặc trả góp tùy dòng tiền.")
    elif burden_ratio > _THRESH_CAUTION:
        overall = (f"Giá xe khá cao so với lương {monthly_salary_million} triệu. "
                   "Gợi ý: tăng đặt cọc, kéo dài kỳ hạn, hoặc xem xét VF 3/VF 5 tiết kiệm hơn.")
    else:
        overall = (f"Mua thẳng khả thi nếu đã có sẵn {total_on_road:.0f} triệu. "
                   "Trả góp cần kiểm soát chi tiêu chặt chẽ.")

    affordability = {
        "monthly_salary_million": monthly_salary_million,
        "scenario_cash":          cash_scenario,
        "scenario_financing_60m": fin_scenario,
        "overall_recommendation": overall,
    }

    result = {
        "status":        "success",
        "model":         f"{car['model']} {car.get('model_version', '')}".strip(),
        "province":      province,
        "range_km":      range_km,
        "on_road_cost":  on_road_cost,
        "monthly_operating_cost": monthly_op,
        "affordability_analysis": affordability,
        "disclaimer":    "Số liệu ước tính. Thuế/phí thực tế có thể thay đổi theo chính sách nhà nước.",
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


# ── TOOL 8: Tìm giá xe tại showroom/đại lý (thời gian thực) ──────────────
@tool
def search_showroom_price(
    model_name: str,
    city: Optional[str] = None,
) -> str:
    """
    Tìm giá xe VinFast tại các showroom / đại lý theo yêu cầu.
    So sánh giá thị trường thực tế với giá niêm yết trong hệ thống.
    Trả về JSON: giá niêm yết từ data, kết quả web, chênh lệch giá (nếu trích xuất được).
    Input:
      - model_name: tên model (VD: 'VF 7 Plus')
      - city: thành phố muốn tìm showroom (tuỳ chọn)
    """
    # 1. Lấy giá niêm yết từ cars.json
    kw = model_name.lower()
    matched_cars = [
        c for c in CARS
        if kw in c["model"].lower() or kw in c.get("model_version", "").lower()
    ]
    listed_prices = [
        {
            "model": f"{c['model']} {c.get('model_version', '')}".strip(),
            "listed_price_million": c.get("price_million"),
        }
        for c in matched_cars if c.get("price_million")
    ]

    # 2. Tìm kiếm giá thực tế trên web
    location_part = f"tại {city}" if city else ""
    queries = [
        f"giá xe VinFast {model_name} {location_part} showroom đại lý 2025 2026",
        f"VinFast {model_name} khuyến mãi ưu đãi {location_part} tháng này",
    ]

    web_results: list[dict] = []
    try:
        for q in queries:
            raw = web_search(q.strip(), max_results=3)
            for r in raw:
                web_results.append({
                    "title":   r["title"],
                    "snippet": _compact(r.get("snippet") or r.get("body", ""))[:250],
                    "url":     r.get("url") or r.get("href", ""),
                })
        # Loại trùng URL
        seen: set[str] = set()
        deduped = []
        for item in web_results:
            if item["url"] not in seen:
                seen.add(item["url"])
                deduped.append(item)
        web_results = deduped[:6]
    except ImportError:
        web_results = [{"title": "Xem giá tại vinfastauto.com",
                        "snippet": "", "url": "https://vinfastauto.com/vn/oto"}]
    except Exception as e:
        web_results = [{"title": f"Lỗi tìm kiếm: {e}",
                        "snippet": "", "url": "https://vinfastauto.com/vn/oto"}]

    # 3. Trích xuất giá từ snippet (tìm pattern "XXX triệu" hoặc "XXX,XXX")
    price_mentions: list[dict] = []
    price_pattern = re.compile(r"(\d[\d.,]+)\s*triệu", re.IGNORECASE)
    for item in web_results:
        found = price_pattern.findall(item["snippet"])
        if found:
            nums = []
            for p in found:
                try:
                    nums.append(float(p.replace(",", "").replace(".", "")))
                except ValueError:
                    pass
            valid = [n for n in nums if 200 <= n <= 5000]  # lọc giá xe hợp lý
            if valid:
                price_mentions.append({
                    "source": item["title"],
                    "prices_million": valid,
                    "url": item["url"],
                })

    # 4. So sánh với giá niêm yết
    comparison: list[dict] = []
    for pm in price_mentions:
        for lp in listed_prices:
            if lp["listed_price_million"]:
                for p in pm["prices_million"]:
                    diff = round(p - lp["listed_price_million"], 1)
                    comparison.append({
                        "model":              lp["model"],
                        "listed_million":     lp["listed_price_million"],
                        "found_million":      p,
                        "difference_million": diff,
                        "note": (
                            "Cao hơn niêm yết" if diff > 0
                            else "Thấp hơn niêm yết / có khuyến mãi" if diff < 0
                            else "Đúng giá niêm yết"
                        ),
                        "source": pm["source"],
                        "url":    pm["url"],
                    })

    result = {
        "status":         "success",
        "model_queried":  model_name,
        "city":           city or "Toàn quốc",
        "listed_prices":  listed_prices if listed_prices
                          else [{"note": f"Chưa có giá niêm yết cho '{model_name}' trong hệ thống"}],
        "web_results":    web_results,
        "price_comparison": comparison if comparison
                            else [{"note": "Không trích xuất được giá cụ thể từ kết quả web"}],
        "disclaimer":     "Giá thị trường biến động — xác nhận trực tiếp với showroom trước khi quyết định.",
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


# ── LangGraph agent ────────────────────────────────────────────────────────
TOOLS = [query_cars, query_maintenance, query_reviews, search_web,
         book_showroom, book_test_drive, calculate_ownership_cost,
         search_showroom_price]

llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0.3)
llm_with_tools = llm.bind_tools(TOOLS)

SYSTEM_PROMPT = """Bạn là trợ lý AI VinFast — hỗ trợ tư vấn mua xe mới và bảo dưỡng xe điện VinFast.

LUỒNG TƯ VẤN MUA XE (hỏi lần lượt, không hỏi dồn):
1. Ngân sách dự kiến (triệu đồng)?
2. Số chỗ ngồi cần thiết?
3. Quãng đường di chuyển thường ngày (km/ngày)?
4. Mục đích: gia đình, cá nhân, hay chạy dịch vụ?
5. Ưu tiên đặc biệt (cốp rộng, tiết kiệm điện, xe to/nhỏ…)?

Khi đủ thông tin → gọi query_cars → gọi query_reviews → gợi ý 2–3 mẫu kèm:
• Ước tính chi phí sở hữu (giá xe + chi phí sạc điện ~1.000–2.000đ/km)
• Pros/cons từ cộng đồng (ghi rõ nguồn)
• Gọi search_showroom_price để so sánh giá showroom thực tế vs niêm yết

LUỒNG HỎI VỀ BẢO DƯỠNG:
→ Gọi query_maintenance với tên model, trả lời rõ bảo hành bao lâu, điều kiện, hotline.

LUỒNG PHÂN TÍCH REVIEW:
→ Nếu user dán đoạn review dài, tóm tắt thành 3 tiêu chí: Hiệu năng / Tiện nghi / Chi phí.
→ Luôn ghi chú "[Ý kiến cộng đồng]" để tách biệt với thông tin hãng.

ĐẶT LỊCH TƯ VẤN TẠI SHOWROOM:
→ Khi user muốn gặp tư vấn viên, hỏi: tên, SĐT, xe quan tâm, ngày giờ, thành phố → gọi book_showroom.
→ book_showroom sẽ tự tìm showroom gần nhất qua web search.

ĐĂNG KÝ LÁI THỬ:
→ Khi user muốn lái thử xe, hỏi: tên, SĐT, model muốn lái thử, ngày giờ, thành phố → gọi book_test_drive.
→ book_test_drive tìm địa điểm lái thử qua web và trả về link đăng ký chính hãng:
   https://shop.vinfastauto.com/vn_vi/dang-ky-lai-thu.html

TÍNH CHI PHÍ SỞ HỮU & PHÂN TÍCH TÀI CHÍNH:
→ Khi user hỏi "giá lăn bánh", "tổng chi phí", "lương X triệu mua được không":
   hỏi: tên model, tỉnh/thành đăng ký, lương tháng (triệu), quãng đường/ngày (km)
   → gọi calculate_ownership_cost → trình bày 3 phần rõ ràng:
   • Giá lăn bánh (phân khoản chi tiết)
   • Chi phí vận hành hằng tháng
   • Phân tích mua thẳng vs trả góp 5 năm so với lương

NGUYÊN TẮC:
- Luôn phân biệt [Thông tin hãng] vs [Ý kiến cộng đồng] vs [Bổ sung từ AI]
- Không cam kết giá khi chưa kiểm tra → dùng search_web
- Nếu AI không chắc → khuyên liên hệ tư vấn viên: 1900 23 23 89
- Trả lời tiếng Việt, ngắn gọn, có dấu đầu dòng, dễ đọc trên mobile"""


class State(TypedDict):
    messages: Annotated[list, add_messages]


def vinfast_agent(state: State) -> dict:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


# Build graph: START → agent ↔ tools → END
graph_builder = StateGraph(State)
graph_builder.add_node("agent", vinfast_agent)
graph_builder.add_node("tools", ToolNode(TOOLS))
graph_builder.add_edge(START, "agent")
graph_builder.add_conditional_edges("agent", tools_condition)
graph_builder.add_edge("tools", "agent")
graph = graph_builder.compile()


# ── CLI ────────────────────────────────────────────────────────────────────
def main() -> None:
    print("=" * 60)
    print("  VinFast AI — Tư vấn mua xe & bảo dưỡng")
    print("  Gõ 'exit' để thoát | 'reset' để bắt đầu lại")
    print("=" * 60)
    print("  Chào bạn! Tôi có thể giúp bạn:")
    print("  • Gợi ý mẫu xe VinFast phù hợp nhu cầu")
    print("  • Tra cứu thông tin bảo dưỡng & bảo hành")
    print("  • Tóm tắt review theo tiêu chí bạn quan tâm")
    print("  • Tìm showroom thực tế & đặt lịch tư vấn")
    print("  • Đăng ký lái thử xe VinFast")
    print("=" * 60)

    state: State = {"messages": []}

    while True:
        try:
            user_input = input("\nBạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTạm biệt!")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit", "thoát"}:
            print("\nVinFast AI: Tạm biệt! Chúc bạn chọn được chiếc xe ưng ý.")
            break

        if user_input.lower() == "reset":
            state = {"messages": []}
            print("\nVinFast AI: Đã bắt đầu cuộc hội thoại mới. Tôi có thể giúp gì cho bạn?")
            continue

        state["messages"].append(HumanMessage(content=user_input))

        try:
            state = graph.invoke(state)
            reply = state["messages"][-1].content
            print(f"\nVinFast AI: {reply}")
        except Exception as e:
            print(f"\n[Lỗi]: {e}")
            print("Vui lòng thử lại hoặc liên hệ hotline: 1900 23 23 89")


if __name__ == "__main__":
    main()
