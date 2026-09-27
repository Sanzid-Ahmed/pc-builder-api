import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .database import get_connection


router = APIRouter(
    prefix="/api/custom-build",
    tags=["Custom Build AI"],
)


# ============================================================
# GEMINI
# ============================================================

try:
    from google import genai
except ImportError:
    genai = None


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash",
)


# ============================================================
# COMPONENTS
# ============================================================

COMPONENT_ORDER = [
    "processor",
    "motherboard",
    "ram",
    "gpu",
    "storage",
    "psu",
    "case",
]


RECOMMENDABLE_COMPONENTS = [
    "motherboard",
    "ram",
    "gpu",
    "storage",
    "psu",
    "case",
]


REQUIRED_COMPONENTS = [
    "processor",
    "motherboard",
    "ram",
    "storage",
    "psu",
    "case",
]


# ============================================================
# REQUEST MODELS
# ============================================================

class BuildRequest(BaseModel):
    processor: dict | None = None
    motherboard: dict | None = None
    ram: dict | None = None
    gpu: dict | None = None
    storage: dict | None = None
    psu: dict | None = None
    case: dict | None = None


class AIBuildRequest(BaseModel):
    budget: float
    priority: str = "balanced"


# ============================================================
# CATEGORY MAP
# ============================================================

CATEGORY_MAP = {
    "processor": [
        "processor",
        "cpu",
    ],
    "motherboard": [
        "motherboard",
        "mother board",
        "mainboard",
    ],
    "ram": [
        "ram",
        "memory",
        "desktop ram",
    ],
    "gpu": [
        "gpu",
        "graphics card",
        "graphic card",
        "graphics",
        "video card",
        "vga",
    ],
    "storage": [
        "storage",
        "ssd",
        "hdd",
        "nvme",
        "hard disk",
        "hard drive",
    ],
    "psu": [
        "psu",
        "power supply",
        "power supply unit",
    ],
    "case": [
        "case",
        "pc case",
        "computer case",
        "casing",
    ],
}


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(value):
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " "),
    )


# ============================================================
# JSON SAFE
# ============================================================

def make_json_safe(value):
    if isinstance(value, Decimal):
        return float(value)

    return value


# ============================================================
# PARSE JSON
# ============================================================

def parse_json(value):
    if not value:
        return {}

    if isinstance(value, dict):
        return value

    if isinstance(value, list):
        return value

    if not isinstance(value, str):
        return {}

    try:
        return json.loads(value)
    except Exception:
        return {}


# ============================================================
# PARSE FEATURES
# ============================================================

def parse_features(value):
    if not value:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, str):
        try:
            parsed = json.loads(value)

            if isinstance(parsed, list):
                return parsed

        except Exception:
            pass

        return [value]

    return []


# ============================================================
# DATABASE ROW → PRODUCT
# ============================================================

def product_to_dict(row):
    return {
        "id": row[0],
        "store": row[1],
        "name": row[2],
        "category": row[3],
        "brand": row[4],
        "product_code": row[5],
        "price": make_json_safe(row[6]),
        "old_price": make_json_safe(row[7]),
        "status": row[8],
        "warranty": row[9],
        "rating": make_json_safe(row[10]),
        "reviews": row[11],
        "url": row[12],
        "images": row[13],
        "features": row[14],
        "specifications": row[15],
    }


# ============================================================
# CATEGORY MATCH
# ============================================================

def category_matches(category, component):
    category = normalize_text(category)

    if not category:
        return False

    allowed_categories = CATEGORY_MAP.get(
        component,
        [],
    )

    for allowed in allowed_categories:
        allowed = normalize_text(allowed)

        if (
            category == allowed
            or category.startswith(allowed + " ")
        ):
            return True

    return False


# ============================================================
# GET ALL PRODUCTS
# ============================================================

def get_all_products():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                store,
                name,
                category,
                brand,
                product_code,
                price,
                old_price,
                status,
                warranty,
                rating,
                reviews,
                url,
                images,
                features,
                specifications
            FROM products
            ORDER BY id DESC
            """
        )

        rows = cursor.fetchall()

        return [
            product_to_dict(row)
            for row in rows
        ]

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# GET SPECIFICATION VALUE
# ============================================================

def get_specification(product, possible_names):
    specifications = parse_json(
        product.get("specifications")
    )

    if not isinstance(specifications, dict):
        return ""

    for key, value in specifications.items():
        normalized_key = normalize_text(key)

        for possible_name in possible_names:
            normalized_name = normalize_text(
                possible_name
            )

            if (
                normalized_key == normalized_name
                or normalized_name in normalized_key
            ):
                return str(value or "").strip()

    return ""


# ============================================================
# PRODUCT TEXT
# ============================================================

def get_product_text(product):
    features = parse_features(
        product.get("features")
    )

    specifications = parse_json(
        product.get("specifications")
    )

    feature_text = " ".join(
        str(item)
        for item in features
    )

    specification_text = " ".join(
        f"{key}: {value}"
        for key, value in specifications.items()
    ) if isinstance(specifications, dict) else ""

    return normalize_text(
        f"""
        {product.get('name', '')}
        {product.get('category', '')}
        {feature_text}
        {specification_text}
        """
    )


# ============================================================
# SOCKET
# ============================================================

def detect_socket(product):
    socket = get_specification(
        product,
        [
            "cpu socket",
            "cpu socket type",
            "socket",
            "socket type",
        ],
    )

    if socket:
        return normalize_text(socket)

    text = get_product_text(product)

    match = re.search(
        r"\blga[\s-]?\d{3,5}\b",
        text,
        re.IGNORECASE,
    )

    if match:
        return normalize_text(
            match.group(0)
        )

    match = re.search(
        r"\b(am4|am5|strx4|swrx8)\b",
        text,
        re.IGNORECASE,
    )

    if match:
        return normalize_text(
            match.group(0)
        )

    return ""


# ============================================================
# MEMORY TYPE
# ============================================================

def detect_memory_type(product):
    memory_type = get_specification(
        product,
        [
            "memory type",
            "ram type",
            "memory technology",
            "supported memory",
            "memory support",
        ],
    )

    if memory_type:
        return normalize_text(
            memory_type
        )

    text = get_product_text(product)

    match = re.search(
        r"\bddr[2345]\b",
        text,
        re.IGNORECASE,
    )

    if match:
        return normalize_text(
            match.group(0)
        )

    return ""


# ============================================================
# FORM FACTOR
# ============================================================

def detect_form_factor(product):
    form_factor = get_specification(
        product,
        [
            "form factor",
            "motherboard form factor",
            "motherboard size",
        ],
    )

    if form_factor:
        return normalize_text(
            form_factor
        )

    text = get_product_text(product)

    match = re.search(
        r"\b(e[\s-]?atx|micro[\s-]?atx|mini[\s-]?itx|atx|itx)\b",
        text,
        re.IGNORECASE,
    )

    if match:
        return normalize_text(
            match.group(0)
        )

    return ""


# ============================================================
# WATTAGE
# ============================================================

def detect_wattage(product):
    wattage = get_specification(
        product,
        [
            "wattage",
            "psu wattage",
            "power supply wattage",
            "power capacity",
            "capacity",
        ],
    )

    if wattage:
        return wattage

    text = get_product_text(product)

    match = re.search(
        r"\b([3-9]\d{2,3})\s*(?:w|watt|watts)\b",
        text,
        re.IGNORECASE,
    )

    if match:
        return match.group(1)

    return ""


# ============================================================
# NUMBER FROM VALUE
# ============================================================

def extract_number(value):
    if value is None:
        return 0

    match = re.search(
        r"\d{2,5}",
        str(value),
    )

    if not match:
        return 0

    try:
        return int(match.group(0))
    except ValueError:
        return 0


# ============================================================
# COMPATIBILITY RESULT
# ============================================================

def compatibility_result(compatible, known):
    return {
        "compatible": compatible,
        "known": known,
    }


# ============================================================
# CPU ↔ MOTHERBOARD
# ============================================================

def cpu_motherboard_compatible(cpu, motherboard):
    cpu_socket = detect_socket(cpu)
    motherboard_socket = detect_socket(
        motherboard
    )

    if not cpu_socket or not motherboard_socket:
        return compatibility_result(
            True,
            False,
        )

    return compatibility_result(
        cpu_socket == motherboard_socket,
        True,
    )


# ============================================================
# CPU ↔ RAM
# ============================================================

def cpu_ram_compatible(cpu, ram):
    cpu_memory = detect_memory_type(cpu)
    ram_memory = detect_memory_type(ram)

    if not cpu_memory or not ram_memory:
        return compatibility_result(
            True,
            False,
        )

    cpu_types = re.findall(
        r"ddr[2345]",
        cpu_memory,
        re.IGNORECASE,
    )

    if not cpu_types:
        return compatibility_result(
            True,
            False,
        )

    return compatibility_result(
        any(
            normalize_text(memory)
            == normalize_text(ram_memory)
            for memory in cpu_types
        ),
        True,
    )


# ============================================================
# MOTHERBOARD ↔ RAM
# ============================================================

def motherboard_ram_compatible(
    motherboard,
    ram,
):
    motherboard_memory = detect_memory_type(
        motherboard
    )

    ram_memory = detect_memory_type(
        ram
    )

    if (
        not motherboard_memory
        or not ram_memory
    ):
        return compatibility_result(
            True,
            False,
        )

    motherboard_types = re.findall(
        r"ddr[2345]",
        motherboard_memory,
        re.IGNORECASE,
    )

    if not motherboard_types:
        return compatibility_result(
            True,
            False,
        )

    return compatibility_result(
        any(
            normalize_text(memory)
            == normalize_text(ram_memory)
            for memory in motherboard_types
        ),
        True,
    )


# ============================================================
# MOTHERBOARD ↔ CASE
# ============================================================

def motherboard_case_compatible(
    motherboard,
    pc_case,
):
    motherboard_form_factor = (
        detect_form_factor(motherboard)
    )

    case_form_factor = (
        detect_form_factor(pc_case)
    )

    if (
        not motherboard_form_factor
        or not case_form_factor
    ):
        return compatibility_result(
            True,
            False,
        )

    motherboard_form_factor = normalize_text(
        motherboard_form_factor
    )

    case_form_factor = normalize_text(
        case_form_factor
    )

    return compatibility_result(
        motherboard_form_factor
        in case_form_factor,
        True,
    )


# ============================================================
# GPU ↔ PSU
# ============================================================

def gpu_psu_compatible(gpu, psu):
    gpu_required = get_specification(
        gpu,
        [
            "recommended psu",
            "recommended power supply",
            "required psu",
            "minimum psu",
        ],
    )

    if not gpu_required:
        gpu_text = get_product_text(gpu)

        match = re.search(
            r"(?:recommended|minimum|required)"
            r".{0,60}?"
            r"\b([3-9]\d{2,3})\s*w\b",
            gpu_text,
            re.IGNORECASE,
        )

        if match:
            gpu_required = match.group(1)

    psu_wattage = detect_wattage(psu)

    required_power = extract_number(
        gpu_required
    )

    available_power = extract_number(
        psu_wattage
    )

    if (
        not required_power
        or not available_power
    ):
        return compatibility_result(
            True,
            False,
        )

    return compatibility_result(
        available_power >= required_power,
        True,
    )


# ============================================================
# TEST PRODUCT AGAINST CURRENT BUILD
# ============================================================

def product_is_compatible(
    component,
    product,
    build,
):
    processor = build.processor
    motherboard = build.motherboard
    ram = build.ram
    gpu = build.gpu
    psu = build.psu
    pc_case = build.case

    # --------------------------------------------------------
    # MOTHERBOARD
    # --------------------------------------------------------

    if component == "motherboard":
        if processor:
            result = cpu_motherboard_compatible(
                processor,
                product,
            )

            if not result["compatible"]:
                return False

        if ram:
            result = motherboard_ram_compatible(
                product,
                ram,
            )

            if not result["compatible"]:
                return False

        if pc_case:
            result = motherboard_case_compatible(
                product,
                pc_case,
            )

            if not result["compatible"]:
                return False

    # --------------------------------------------------------
    # RAM
    # --------------------------------------------------------

    elif component == "ram":
        if processor:
            result = cpu_ram_compatible(
                processor,
                product,
            )

            if not result["compatible"]:
                return False

        if motherboard:
            result = motherboard_ram_compatible(
                motherboard,
                product,
            )

            if not result["compatible"]:
                return False

    # --------------------------------------------------------
    # GPU
    # --------------------------------------------------------

    elif component == "gpu":
        if psu:
            result = gpu_psu_compatible(
                product,
                psu,
            )

            if not result["compatible"]:
                return False

    # --------------------------------------------------------
    # PSU
    # --------------------------------------------------------

    elif component == "psu":
        if gpu:
            result = gpu_psu_compatible(
                gpu,
                product,
            )

            if not result["compatible"]:
                return False

    # --------------------------------------------------------
    # CASE
    # --------------------------------------------------------

    elif component == "case":
        if motherboard:
            result = motherboard_case_compatible(
                motherboard,
                product,
            )

            if not result["compatible"]:
                return False

    return True


# ============================================================
# FILTER PRODUCTS
# ============================================================

def filter_products_for_build(
    products,
    component,
    build,
):
    filtered = []

    for product in products:
        if not category_matches(
            product.get("category"),
            component,
        ):
            continue

        if not product_is_compatible(
            component,
            product,
            build,
        ):
            continue

        filtered.append(product)

    return filtered


# ============================================================
# PRODUCT PRICE
# ============================================================

def product_price(product):
    try:
        return float(
            product.get("price") or 0
        )
    except (TypeError, ValueError):
        return 0


# ============================================================
# PRODUCT RATING
# ============================================================

def product_rating(product):
    try:
        return float(
            product.get("rating") or 0
        )
    except (TypeError, ValueError):
        return 0


# ============================================================
# SELECT AI CANDIDATES
# ============================================================

def select_products_for_ai(
    products,
    limit=18,
):
    if not products:
        return []

    priced = [
        product
        for product in products
        if product_price(product) > 0
    ]

    if not priced:
        return products[:limit]

    # Sort by price.
    by_price = sorted(
        priced,
        key=product_price,
    )

    # Sort by rating.
    by_rating = sorted(
        priced,
        key=product_rating,
        reverse=True,
    )

    selected = []
    selected_ids = set()

    def add_product(product):
        product_id = str(
            product.get("id")
        )

        if product_id in selected_ids:
            return

        selected_ids.add(product_id)
        selected.append(product)

    # Lower-price/value options.
    for product in by_price[:6]:
        add_product(product)

    # Higher-rated options.
    for product in by_rating[:6]:
        add_product(product)

    # Middle-price options.
    middle_start = max(
        0,
        len(by_price) // 3,
    )

    for product in by_price[
        middle_start:middle_start + 8
    ]:
        add_product(product)

    return selected[:limit]


# ============================================================
# CLEAN PRODUCT FOR AI
# ============================================================

def clean_product_for_ai(product):
    features = parse_features(
        product.get("features")
    )

    specifications = parse_json(
        product.get("specifications")
    )

    if not isinstance(
        specifications,
        dict,
    ):
        specifications = {}

    return {
        "id": product.get("id"),
        "name": product.get("name"),
        "brand": product.get("brand"),
        "category": product.get("category"),
        "price": product.get("price"),
        "rating": product.get("rating"),
        "reviews": product.get("reviews"),
        "socket": detect_socket(product),
        "memory_type": detect_memory_type(
            product
        ),
        "form_factor": detect_form_factor(
            product
        ),
        "wattage": detect_wattage(
            product
        ),
        "features": features[:12],
        "specifications": specifications,
    }


# ============================================================
# CURRENT BUILD → AI DATA
# ============================================================

def build_for_ai(build):
    result = {}

    for component in COMPONENT_ORDER:
        selected = getattr(
            build,
            component,
        )

        if selected:
            result[component] = {
                "id": selected.get("id"),
                "name": selected.get("name"),
                "brand": selected.get("brand"),
                "category": selected.get("category"),
                "price": selected.get("price"),
                "socket": detect_socket(selected),
                "memory_type": detect_memory_type(
                    selected
                ),
                "form_factor": detect_form_factor(
                    selected
                ),
                "wattage": detect_wattage(
                    selected
                ),
            }

    return result


# ============================================================
# MISSING COMPONENTS
# ============================================================

def get_missing_components(build):
    return [
        component
        for component in RECOMMENDABLE_COMPONENTS
        if not getattr(
            build,
            component,
        )
    ]


# ============================================================
# GEMINI
# ============================================================

def ask_gemini(prompt):
    if genai is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "Gemini SDK is not installed. "
                "Install google-genai."
            ),
        )

    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail=(
                "GEMINI_API_KEY is not configured."
            ),
        )

    try:
        client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )

        response_text = (
            response.text or ""
        ).strip()

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Gemini API error: {error}",
        )

    if not response_text:
        raise HTTPException(
            status_code=500,
            detail=(
                "Gemini returned an empty response."
            ),
        )

    # Remove markdown code fences.
    response_text = re.sub(
        r"^```json\s*",
        "",
        response_text,
        flags=re.IGNORECASE,
    )

    response_text = re.sub(
        r"^```\s*",
        "",
        response_text,
    )

    response_text = re.sub(
        r"\s*```$",
        "",
        response_text,
    )

    response_text = response_text.strip()

    try:
        return json.loads(
            response_text
        )

    except json.JSONDecodeError:
        match = re.search(
            r"\{.*\}",
            response_text,
            re.DOTALL,
        )

        if not match:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Gemini returned invalid JSON."
                ),
            )

        try:
            return json.loads(
                match.group(0)
            )

        except json.JSONDecodeError:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Could not parse Gemini JSON."
                ),
            )


# ============================================================
# SUGGESTION PROMPT
# ============================================================

def create_suggestion_prompt(
    build,
    product_groups,
):
    current_build = build_for_ai(build)

    return f"""
You are an expert PC building assistant.

The user is manually building a desktop PC.

CURRENT BUILD:

{json.dumps(
    current_build,
    indent=2,
    default=str,
)}

COMPATIBLE PRODUCT OPTIONS:

{json.dumps(
    product_groups,
    indent=2,
    default=str,
)}

Your job is to recommend the most suitable products
from the provided options.

IMPORTANT RULES:

1. Use ONLY products from the provided data.
2. Never invent a product.
3. Never invent a product ID.
4. Every product_id must exist in the provided data.
5. Do not recommend an already selected component.
6. Compatibility has already been checked by the backend.
7. Consider price and value.
8. Consider the user's existing components.
9. Prefer balanced and practical choices.
10. GPU is optional.
11. Give at most 2 suggestions per missing component.
12. Keep each reason short and useful.

Return ONLY valid JSON.

Format:

{{
    "suggestions": [
        {{
            "component": "motherboard",
            "product_id": 123,
            "reason": "Compatible socket with good features for this build."
        }}
    ],
    "message": "Short explanation of the recommendations."
}}

Allowed component values:

motherboard
ram
gpu
storage
psu
case
"""


# ============================================================
# AUTO BUILD PROMPT
# ============================================================

def create_auto_build_prompt(
    budget,
    priority,
    product_groups,
):
    return f"""
You are an expert PC building assistant.

Create a complete desktop PC build for the user.

USER BUDGET:

{budget}

USER PRIORITY:

{priority}

AVAILABLE COMPATIBLE PRODUCTS:

{json.dumps(
    product_groups,
    indent=2,
    default=str,
)}

IMPORTANT RULES:

1. Use ONLY products from the supplied data.
2. Never invent products.
3. Never invent product IDs.
4. Every selected product_id must exist in the supplied data.
5. Stay within the user's budget as closely as practical.
6. The total selected price must NOT exceed the budget.
7. Select exactly one processor.
8. Select exactly one motherboard.
9. Select exactly one RAM product.
10. GPU is optional, but include one when appropriate for the user's priority and budget.
11. Select exactly one storage product.
12. Select exactly one PSU.
13. Select exactly one case.
14. Prefer a balanced build rather than spending almost all money on one component.
15. Consider the user's priority when distributing the budget.
16. Prefer better value when products have similar performance.
17. Do not select duplicate products.
18. Only choose from the provided compatible candidates.

PRIORITY GUIDANCE:

gaming:
Prioritize GPU performance, then CPU, RAM and storage.

productivity:
Prioritize CPU, RAM and reliable storage.

programming:
Prioritize CPU, RAM, storage and overall value.

content_creation:
Prioritize CPU, GPU, RAM and storage.

balanced:
Distribute the budget reasonably across the complete build.

Return ONLY valid JSON.

Format:

{{
    "build": {{
        "processor": 123,
        "motherboard": 456,
        "ram": 789,
        "gpu": 111,
        "storage": 222,
        "psu": 333,
        "case": 444
    }},
    "message": "Short explanation of why this build is balanced for the user."
}}

If a GPU is not appropriate for the budget, use:

"gpu": null
"""


# ============================================================
# VERIFY AI SUGGESTIONS
# ============================================================

def attach_real_products(
    gemini_result,
    all_products,
    build=None,
):
    products_by_id = {
        str(product["id"]): product
        for product in all_products
    }

    suggestions = gemini_result.get(
        "suggestions",
        [],
    )

    if not isinstance(
        suggestions,
        list,
    ):
        return []

    final = []

    for suggestion in suggestions:
        if not isinstance(
            suggestion,
            dict,
        ):
            continue

        component = suggestion.get(
            "component"
        )

        product_id = suggestion.get(
            "product_id"
        )

        reason = suggestion.get(
            "reason",
            "",
        )

        if component not in RECOMMENDABLE_COMPONENTS:
            continue

        if product_id is None:
            continue

        product = products_by_id.get(
            str(product_id)
        )

        if not product:
            continue

        if not category_matches(
            product.get("category"),
            component,
        ):
            continue

        if build and getattr(
            build,
            component,
        ):
            continue

        if build and not product_is_compatible(
            component,
            product,
            build,
        ):
            continue

        final.append(
            {
                "component": component,
                "product": product,
                "reason": str(reason),
            }
        )

    return final


# ============================================================
# VERIFY AUTO BUILD
# ============================================================

def attach_auto_build_products(
    gemini_result,
    candidate_products,
):
    build_result = gemini_result.get(
        "build",
        {},
    )

    if not isinstance(
        build_result,
        dict,
    ):
        return None

    products_by_id = {
        str(product["id"]): product
        for product in candidate_products
    }

    final_build = {}

    for component in COMPONENT_ORDER:
        product_id = build_result.get(
            component
        )

        # GPU is optional.
        if (
            component == "gpu"
            and product_id is None
        ):
            final_build[component] = None
            continue

        if product_id is None:
            return None

        product = products_by_id.get(
            str(product_id)
        )

        if not product:
            return None

        if not category_matches(
            product.get("category"),
            component,
        ):
            return None

        final_build[component] = product

    return final_build


# ============================================================
# BUILD TOTAL
# ============================================================

def calculate_build_total(build):
    total = 0

    for component in COMPONENT_ORDER:
        product = build.get(component)

        if not product:
            continue

        total += product_price(product)

    return round(total, 2)


# ============================================================
# ESTIMATE POWER
# ============================================================

def estimate_component_power(product):
    if not product:
        return 0

    text = get_product_text(product)

    wattage = detect_wattage(product)

    value = extract_number(wattage)

    if value:
        return value

    # Conservative fallback based on component text.
    if category_matches(
        product.get("category"),
        "processor",
    ):
        if "ryzen 9" in text or "core i9" in text:
            return 170

        if "ryzen 7" in text or "core i7" in text:
            return 125

        return 90

    if category_matches(
        product.get("category"),
        "gpu",
    ):
        return 200

    return 0


def estimate_build_power(build):
    processor = build.get("processor")
    gpu = build.get("gpu")

    processor_power = estimate_component_power(
        processor
    )

    gpu_power = estimate_component_power(
        gpu
    )

    # Additional motherboard/RAM/storage/fan allowance.
    platform_power = 80

    total = (
        processor_power
        + gpu_power
        + platform_power
    )

    return int(total)


# ============================================================
# API: AI SUGGESTIONS
# ============================================================

@router.post(
    "/ai-suggestions"
)
def ai_suggestions(
    build: BuildRequest,
):
    if not build.processor:
        return {
            "success": True,
            "message": (
                "Select a processor or use AI Build "
                "to generate a complete PC automatically."
            ),
            "suggestions": [],
        }

    missing_components = (
        get_missing_components(build)
    )

    if not missing_components:
        return {
            "success": True,
            "message": (
                "Your build contains all required components."
            ),
            "suggestions": [],
        }

    all_database_products = get_all_products()

    product_groups = {}
    all_candidate_products = []

    for component in missing_components:
        component_products = (
            filter_products_for_build(
                all_database_products,
                component,
                build,
            )
        )

        component_products = (
            select_products_for_ai(
                component_products,
                limit=18,
            )
        )

        product_groups[component] = [
            clean_product_for_ai(product)
            for product in component_products
        ]

        all_candidate_products.extend(
            component_products
        )

    if not all_candidate_products:
        return {
            "success": True,
            "message": (
                "No compatible products were found "
                "for the current build."
            ),
            "suggestions": [],
        }

    prompt = create_suggestion_prompt(
        build,
        product_groups,
    )

    gemini_result = ask_gemini(
        prompt
    )

    suggestions = attach_real_products(
        gemini_result,
        all_candidate_products,
        build,
    )

    return {
        "success": True,
        "message": gemini_result.get(
            "message",
            "Here are some suggestions for your build.",
        ),
        "suggestions": suggestions[:12],
    }


# ============================================================
# API: AI AUTO BUILD
# ============================================================

@router.post(
    "/ai-build"
)
def ai_build(
    request: AIBuildRequest,
):
    # --------------------------------------------------------
    # VALIDATE BUDGET
    # --------------------------------------------------------

    if request.budget <= 0:
        raise HTTPException(
            status_code=400,
            detail="Budget must be greater than zero.",
        )

    if request.budget < 10000:
        raise HTTPException(
            status_code=400,
            detail=(
                "The budget is too low for a complete desktop PC build."
            ),
        )

    priority = normalize_text(
        request.priority
    )

    allowed_priorities = {
        "gaming",
        "productivity",
        "programming",
        "content_creation",
        "balanced",
    }

    if priority not in allowed_priorities:
        priority = "balanced"

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    all_database_products = get_all_products()

    empty_build = BuildRequest()

    product_groups = {}
    all_candidate_products = []

    # --------------------------------------------------------
    # GET CANDIDATES
    # --------------------------------------------------------

    for component in COMPONENT_ORDER:
        component_products = (
            filter_products_for_build(
                all_database_products,
                component,
                empty_build,
            )
        )

        # Remove products that are clearly above the budget.
        component_products = [
            product
            for product in component_products
            if (
                product_price(product) == 0
                or product_price(product)
                <= request.budget
            )
        ]

        component_products = (
            select_products_for_ai(
                component_products,
                limit=18,
            )
        )

        product_groups[component] = [
            clean_product_for_ai(product)
            for product in component_products
        ]

        all_candidate_products.extend(
            component_products
        )

    # --------------------------------------------------------
    # CHECK CANDIDATES
    # --------------------------------------------------------

    required_candidate_components = [
        component
        for component in REQUIRED_COMPONENTS
        if product_groups.get(component)
    ]

    if len(required_candidate_components) < len(
        REQUIRED_COMPONENTS
    ):
        return {
            "success": False,
            "message": (
                "There are not enough compatible products "
                "to create a complete build."
            ),
            "build": None,
        }

    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    prompt = create_auto_build_prompt(
        request.budget,
        priority,
        product_groups,
    )

    gemini_result = ask_gemini(
        prompt
    )

    # --------------------------------------------------------
    # VERIFY PRODUCTS
    # --------------------------------------------------------

    generated_build = attach_auto_build_products(
        gemini_result,
        all_candidate_products,
    )

    if not generated_build:
        raise HTTPException(
            status_code=500,
            detail=(
                "AI returned an invalid build. "
                "Please try again."
            ),
        )

    # --------------------------------------------------------
    # FINAL COMPATIBILITY VERIFICATION
    # --------------------------------------------------------

    final_build_request = BuildRequest(
        **generated_build
    )

    for component in COMPONENT_ORDER:
        product = generated_build.get(
            component
        )

        if not product:
            continue

        if not product_is_compatible(
            component,
            product,
            final_build_request,
        ):
            raise HTTPException(
                status_code=500,
                detail=(
                    "AI generated a build that failed "
                    "the final compatibility check."
                ),
            )

    # --------------------------------------------------------
    # TOTAL
    # --------------------------------------------------------

    total_price = calculate_build_total(
        generated_build
    )

    # --------------------------------------------------------
    # BUDGET VERIFICATION
    # --------------------------------------------------------

    if total_price > request.budget:
        raise HTTPException(
            status_code=500,
            detail=(
                "AI generated a build above the requested budget. "
                "Please try again."
            ),
        )

    # --------------------------------------------------------
    # POWER
    # --------------------------------------------------------

    estimated_power = estimate_build_power(
        generated_build
    )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "success": True,
        "message": gemini_result.get(
            "message",
            "AI generated a complete PC build.",
        ),
        "priority": priority,
        "budget": request.budget,
        "total_price": total_price,
        "estimated_power": estimated_power,
        "build": generated_build,
    }