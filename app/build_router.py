import re
import time
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .database import get_connection


router = APIRouter(prefix="/api", tags=["PC Builder"])


# ============================================================
# REQUEST MODEL
# ============================================================

class BuildRequest(BaseModel):
    type: str
    budget: float
    priority: str
    ram: str
    storage: str


# ============================================================
# CATEGORY MAP
# ============================================================

CATEGORY_FIELD_MAP = {
    "Processor": ["Processor"],
    "Motherboard": ["Motherboard"],
    "RAM": ["RAM", "RAM (Desktop)"],
    "Graphics Card": ["Graphics Card"],
    "SSD": ["SSD"],
    "Hard Disk Drive": ["Hard Disk Drive"],
    "CPU Cooler": ["CPU Cooler"],
    "Power Supply": ["Power Supply"],
    "Casing": ["Casing"],
}


# ============================================================
# BASIC HELPERS
# ============================================================

def safe_price(product):
    try:
        price = product.get("price")

        if isinstance(price, Decimal):
            price = float(price)

        price = float(price)

        if price <= 0:
            return None

        return price

    except (TypeError, ValueError):
        return None


def product_to_dict(product):
    result = dict(product)

    if isinstance(result.get("price"), Decimal):
        result["price"] = float(result["price"])

    if isinstance(result.get("old_price"), Decimal):
        result["old_price"] = float(result["old_price"])

    return result


def product_text(product):
    parts = [
        str(product.get("name", "")),
        str(product.get("brand", "")),
        str(product.get("features", "")),
        str(product.get("specifications", "")),
    ]

    return " ".join(parts).lower()


def is_available(product):
    status = str(product.get("status", "")).lower().strip()

    unavailable_words = [
        "out of stock",
        "out-of-stock",
        "unavailable",
        "not available",
    ]

    return not any(
        word in status
        for word in unavailable_words
    )


# ============================================================
# CAPACITY
# ============================================================

def extract_capacity_gb(product):
    text = product_text(product)

    # TB
    tb_matches = re.findall(
        r"(\d+(?:\.\d+)?)\s*(?:tb|t\.b\.)",
        text
    )

    if tb_matches:
        values = []

        for value in tb_matches:
            try:
                values.append(float(value) * 1024)
            except ValueError:
                pass

        if values:
            return max(values)

    # GB
    gb_matches = re.findall(
        r"(\d+(?:\.\d+)?)\s*(?:gb|g\.b\.)",
        text
    )

    if gb_matches:
        values = []

        for value in gb_matches:
            try:
                values.append(float(value))
            except ValueError:
                pass

        if values:
            return max(values)

    return None


def requested_capacity_gb(value):
    text = str(value).lower()

    # TB
    tb_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:tb|t\.b\.)",
        text
    )

    if tb_match:
        return float(tb_match.group(1)) * 1024

    # GB
    gb_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:gb|g\.b\.)",
        text
    )

    if gb_match:
        return float(gb_match.group(1))

    return None


def storage_requires_hdd(storage):
    text = str(storage).lower()

    return (
        "hdd" in text
        or "hard disk" in text
        or "hard drive" in text
    )


# ============================================================
# CPU / MOTHERBOARD PLATFORM
# ============================================================

def detect_platform(product):
    text = product_text(product)

    intel_words = [
        "intel",
        "core i3",
        "core i5",
        "core i7",
        "core i9",
        "lga",
    ]

    amd_words = [
        "amd",
        "ryzen",
        "athlon",
        "am4",
        "am5",
    ]

    has_intel = any(
        word in text
        for word in intel_words
    )

    has_amd = any(
        word in text
        for word in amd_words
    )

    if has_intel and not has_amd:
        return "intel"

    if has_amd and not has_intel:
        return "amd"

    return "unknown"


def motherboard_compatible(
    motherboard,
    cpu_platform
):
    if cpu_platform == "unknown":
        return True

    platform = detect_platform(motherboard)

    if platform == "unknown":
        return True

    return platform == cpu_platform


# ============================================================
# PERFORMANCE SCORES
# ============================================================

def cpu_score(product):
    text = product_text(product)

    score = 0

    patterns = [
        (r"\bi9\b", 100),
        (r"\bi7\b", 85),
        (r"\bi5\b", 70),
        (r"\bi3\b", 50),

        (r"ryzen\s*9", 100),
        (r"ryzen\s*7", 85),
        (r"ryzen\s*5", 70),
        (r"ryzen\s*3", 50),
    ]

    for pattern, points in patterns:
        if re.search(pattern, text):
            score += points
            break

    # Newer Intel generation bonus
    intel_generation_matches = re.findall(
        r"\bi[3579][-\s]?([1-9][0-9]{2,3})\b",
        text
    )

    if intel_generation_matches:
        try:
            model_number = max(
                int(x)
                for x in intel_generation_matches
            )

            if model_number >= 14000:
                score += 20
            elif model_number >= 12000:
                score += 15
            elif model_number >= 10000:
                score += 10

        except ValueError:
            pass

    # Ryzen generation bonus
    ryzen_matches = re.findall(
        r"ryzen\s*[3579]\s*(\d{4})",
        text
    )

    if ryzen_matches:
        try:
            generation_number = max(
                int(x)
                for x in ryzen_matches
            )

            if generation_number >= 7000:
                score += 20
            elif generation_number >= 5000:
                score += 15
            elif generation_number >= 3000:
                score += 10

        except ValueError:
            pass

    return score


def gpu_score(product):
    text = product_text(product)

    gpu_patterns = [
        ("rtx 5090", 150),
        ("rtx 5080", 140),
        ("rtx 5070", 125),
        ("rtx 5060", 110),

        ("rtx 4090", 145),
        ("rtx 4080", 135),
        ("rtx 4070", 120),
        ("rtx 4060", 105),

        ("rtx 3090", 115),
        ("rtx 3080", 110),
        ("rtx 3070", 100),
        ("rtx 3060", 90),
        ("rtx 3050", 70),

        ("gtx 1660", 60),
        ("gtx 1650", 50),

        ("rx 7900", 130),
        ("rx 7800", 115),
        ("rx 7700", 105),
        ("rx 7600", 90),

        ("rx 6700", 90),
        ("rx 6600", 75),

        ("gt 730", 20),
    ]

    for name, points in gpu_patterns:
        if name in text:
            return points

    return 0


# ============================================================
# FILTERING
# ============================================================

def valid_products(products):
    return [
        product
        for product in products
        if safe_price(product) is not None
    ]


def capacity_products(
    products,
    required_capacity
):
    products = valid_products(products)

    if required_capacity is None:
        return products

    matching = []

    for product in products:
        capacity = extract_capacity_gb(product)

        if capacity is not None:
            if capacity >= required_capacity:
                matching.append(product)

    return matching


def available_first(products):
    if not products:
        return []

    available = [
        product
        for product in products
        if is_available(product)
    ]

    if available:
        return available

    # If no product is marked available,
    # use all valid products.
    return products


def cheapest(products):
    products = valid_products(products)

    if not products:
        return None

    products = available_first(products)

    return min(
        products,
        key=lambda product: safe_price(product)
    )


# ============================================================
# CANDIDATE SELECTION
# ============================================================

def get_candidates(
    products,
    kind=None,
    required_capacity=None,
    limit=12
):
    products = capacity_products(
        products,
        required_capacity
    )

    if not products:
        return []

    products = available_first(products)

    # --------------------------------------------------------
    # CPU
    # --------------------------------------------------------

    if kind == "cpu":

        cheapest_products = sorted(
            products,
            key=lambda x: safe_price(x)
        )[:6]

        powerful_products = sorted(
            products,
            key=lambda x: cpu_score(x),
            reverse=True
        )[:8]

        merged = {}

        for product in cheapest_products:
            merged[product["id"]] = product

        for product in powerful_products:
            merged[product["id"]] = product

        return list(merged.values())[:limit]

    # --------------------------------------------------------
    # GPU
    # --------------------------------------------------------

    if kind == "gpu":

        cheapest_products = sorted(
            products,
            key=lambda x: safe_price(x)
        )[:6]

        powerful_products = sorted(
            products,
            key=lambda x: gpu_score(x),
            reverse=True
        )[:8]

        merged = {}

        for product in cheapest_products:
            merged[product["id"]] = product

        for product in powerful_products:
            merged[product["id"]] = product

        return list(merged.values())[:limit]

    # --------------------------------------------------------
    # Other components
    # --------------------------------------------------------

    return sorted(
        products,
        key=lambda x: safe_price(x)
    )[:limit]


# ============================================================
# BUILD GENERATOR
# ============================================================

def generate_local_build(
    grouped,
    request
):
    start_time = time.time()

    budget = float(request.budget)

    print("==========================================")
    print("LOCAL BUILD GENERATION")
    print("Gemini is NOT being used.")
    print("==========================================")

    ram_capacity = requested_capacity_gb(
        request.ram
    )

    storage_capacity = requested_capacity_gb(
        request.storage
    )

    wants_hdd = storage_requires_hdd(
        request.storage
    )

    # ========================================================
    # RAM
    # ========================================================

    ram_products = (
        grouped.get("RAM", [])
        + grouped.get("RAM (Desktop)", [])
    )

    ram_candidates = get_candidates(
        ram_products,
        required_capacity=ram_capacity,
        limit=8
    )

    if not ram_candidates:
        raise HTTPException(
            status_code=400,
            detail=f"No RAM matching {request.ram} was found."
        )

    # ========================================================
    # SSD
    # ========================================================

    ssd_candidates = get_candidates(
        grouped.get("SSD", []),
        required_capacity=storage_capacity,
        limit=8
    )

    if not ssd_candidates:
        raise HTTPException(
            status_code=400,
            detail=f"No SSD matching {request.storage} was found."
        )

    # ========================================================
    # HDD
    # ========================================================

    hdd_candidates = []

    if wants_hdd:

        hdd_candidates = get_candidates(
            grouped.get("Hard Disk Drive", []),
            limit=6
        )

        if not hdd_candidates:
            raise HTTPException(
                status_code=400,
                detail="No suitable Hard Disk Drive was found."
            )

    # ========================================================
    # COOLER
    # ========================================================

    cooler_candidates = get_candidates(
        grouped.get("CPU Cooler", []),
        limit=8
    )

    # ========================================================
    # PSU
    # ========================================================

    psu_candidates = get_candidates(
        grouped.get("Power Supply", []),
        limit=8
    )

    # ========================================================
    # CASING
    # ========================================================

    casing_candidates = get_candidates(
        grouped.get("Casing", []),
        limit=8
    )

    # ========================================================
    # MOTHERBOARD
    # ========================================================

    motherboard_products = valid_products(
        grouped.get("Motherboard", [])
    )

    motherboard_products = available_first(
        motherboard_products
    )

    if not motherboard_products:
        raise HTTPException(
            status_code=400,
            detail="No suitable Motherboard was found."
        )

    # ========================================================
    # CPU
    # ========================================================

    cpu_candidates = get_candidates(
        grouped.get("Processor", []),
        kind="cpu",
        limit=14
    )

    if not cpu_candidates:
        raise HTTPException(
            status_code=400,
            detail="No suitable Processor was found."
        )

    # ========================================================
    # GPU
    # ========================================================

    gpu_candidates = get_candidates(
        grouped.get("Graphics Card", []),
        kind="gpu",
        limit=14
    )

    if not gpu_candidates:
        raise HTTPException(
            status_code=400,
            detail="No suitable Graphics Card was found."
        )

    # ========================================================
    # CHEAPEST REQUIRED COMPONENTS
    # ========================================================

    cheapest_ram = cheapest(
        ram_candidates
    )

    cheapest_ssd = cheapest(
        ssd_candidates
    )

    cheapest_cooler = cheapest(
        cooler_candidates
    )

    cheapest_psu = cheapest(
        psu_candidates
    )

    cheapest_casing = cheapest(
        casing_candidates
    )

    cheapest_hdd = None

    if wants_hdd:
        cheapest_hdd = cheapest(
            hdd_candidates
        )

    if not all([
        cheapest_ram,
        cheapest_ssd,
        cheapest_cooler,
        cheapest_psu,
        cheapest_casing
    ]):
        raise HTTPException(
            status_code=400,
            detail=(
                "Some required PC components are "
                "missing from the database."
            )
        )

    if wants_hdd and not cheapest_hdd:
        raise HTTPException(
            status_code=400,
            detail="No suitable Hard Disk Drive was found."
        )

    # ========================================================
    # BUILD TYPE / PRIORITY
    # ========================================================

    build_type = str(
        request.type
    ).lower().strip()

    priority = str(
        request.priority
    ).lower().strip()

    # ========================================================
    # PREPARE MOTHERBOARDS
    # ========================================================

    motherboard_cache = {}

    for cpu in cpu_candidates:

        cpu_platform = detect_platform(cpu)

        compatible = [
            motherboard
            for motherboard in motherboard_products
            if motherboard_compatible(
                motherboard,
                cpu_platform
            )
        ]

        compatible = sorted(
            compatible,
            key=lambda x: safe_price(x)
        )[:5]

        motherboard_cache[
            cpu.get("id")
        ] = compatible

    # ========================================================
    # FIND COMPLETE BUILD
    # ========================================================

    best_build = None
    best_score = float("-inf")

    combinations_checked = 0

    for cpu in cpu_candidates:

        cpu_price = safe_price(cpu)

        if cpu_price is None:
            continue

        compatible_motherboards = motherboard_cache.get(
            cpu.get("id"),
            []
        )

        if not compatible_motherboards:
            continue

        cpu_platform = detect_platform(cpu)

        for gpu in gpu_candidates:

            gpu_price = safe_price(gpu)

            if gpu_price is None:
                continue

            # ------------------------------------------------
            # Fast preliminary budget check
            # ------------------------------------------------

            minimum_without_motherboard = (
                cpu_price
                + gpu_price
                + safe_price(cheapest_ram)
                + safe_price(cheapest_ssd)
                + safe_price(cheapest_cooler)
                + safe_price(cheapest_psu)
                + safe_price(cheapest_casing)
            )

            if wants_hdd:
                minimum_without_motherboard += safe_price(
                    cheapest_hdd
                )

            # Even the cheapest motherboard cannot fit
            # if this amount is already over budget.
            cheapest_motherboard_price = safe_price(
                compatible_motherboards[0]
            )

            if (
                minimum_without_motherboard
                + cheapest_motherboard_price
                > budget
            ):
                continue

            # ------------------------------------------------
            # Motherboards
            # ------------------------------------------------

            for motherboard in compatible_motherboards:

                combinations_checked += 1

                motherboard_price = safe_price(
                    motherboard
                )

                if motherboard_price is None:
                    continue

                components = [
                    cpu,
                    motherboard,
                    cheapest_ram,
                    gpu,
                    cheapest_ssd,
                    cheapest_cooler,
                    cheapest_psu,
                    cheapest_casing,
                ]

                if wants_hdd:
                    components.append(
                        cheapest_hdd
                    )

                total = sum(
                    safe_price(component)
                    for component in components
                )

                # ------------------------------------------------
                # Budget check
                # ------------------------------------------------

                if total > budget:
                    continue

                # ------------------------------------------------
                # Performance
                # ------------------------------------------------

                cpu_performance = cpu_score(cpu)
                gpu_performance = gpu_score(gpu)

                spending = (
                    total / budget
                    if budget > 0
                    else 0
                )

                # =================================================
                # GAMING BUILD
                # =================================================

                if build_type == "gaming":

                    if (
                        "maximum" in priority
                        or "performance" in priority
                    ):
                        score = (
                            gpu_performance * 100
                            + cpu_performance * 50
                            + spending * 30
                        )

                    else:
                        score = (
                            gpu_performance * 80
                            + cpu_performance * 40
                            + spending * 30
                        )

                # =================================================
                # PRODUCTIVITY / OTHER
                # =================================================

                else:

                    score = (
                        cpu_performance * 70
                        + gpu_performance * 30
                        + spending * 25
                    )

                # =================================================
                # SELECT BEST BUILD
                # =================================================

                if score > best_score:

                    best_score = score

                    best_build = {
                        "Processor": cpu,
                        "Motherboard": motherboard,
                        "RAM": cheapest_ram,
                        "Graphics Card": gpu,
                        "SSD": cheapest_ssd,
                        "CPU Cooler": cheapest_cooler,
                        "Power Supply": cheapest_psu,
                        "Casing": cheapest_casing,
                    }

                    if wants_hdd:
                        best_build[
                            "Hard Disk Drive"
                        ] = cheapest_hdd

    # ========================================================
    # NO BUILD
    # ========================================================

    if best_build is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "No complete PC build can fit within "
                "this budget with the selected RAM "
                "and storage requirements."
            )
        )

    # ========================================================
    # FINAL TOTAL
    # ========================================================

    total_price = sum(
        safe_price(product)
        for product in best_build.values()
    )

    elapsed = time.time() - start_time

    print("==========================================")
    print("BUILD SELECTED")
    print("==========================================")

    for category, product in best_build.items():

        print(
            f"{category}: "
            f"{product.get('name')} "
            f"৳{safe_price(product):,.0f}"
        )

    print("------------------------------------------")
    print(
        f"Total: ৳{total_price:,.0f}"
    )

    print(
        f"Budget: ৳{budget:,.0f}"
    )

    print(
        f"Combinations checked: "
        f"{combinations_checked}"
    )

    print(
        f"Generation time: "
        f"{elapsed:.2f} seconds"
    )

    print("==========================================")

    return best_build


# ============================================================
# VALIDATION
# ============================================================

def validate_build(
    build,
    request
):
    budget = float(request.budget)

    if not build:
        raise HTTPException(
            status_code=400,
            detail="Build generation failed."
        )

    # ========================================================
    # DUPLICATE PRODUCTS
    # ========================================================

    ids = [
        product.get("id")
        for product in build.values()
    ]

    if len(ids) != len(set(ids)):
        raise HTTPException(
            status_code=400,
            detail="Build contains duplicate products."
        )

    # ========================================================
    # PRICE VALIDATION
    # ========================================================

    for category, product in build.items():

        price = safe_price(product)

        if price is None:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid price for {category}."
            )

    # ========================================================
    # TOTAL
    # ========================================================

    total = sum(
        safe_price(product)
        for product in build.values()
    )

    if total > budget:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Build exceeds budget. "
                f"Total: ৳{total:,.0f}, "
                f"Budget: ৳{budget:,.0f}"
            )
        )

    # ========================================================
    # CPU / MOTHERBOARD COMPATIBILITY
    # ========================================================

    if (
        "Processor" in build
        and "Motherboard" in build
    ):

        cpu_platform = detect_platform(
            build["Processor"]
        )

        motherboard_platform = detect_platform(
            build["Motherboard"]
        )

        if (
            cpu_platform != "unknown"
            and motherboard_platform != "unknown"
            and cpu_platform != motherboard_platform
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Processor and motherboard "
                    "platform are incompatible."
                )
            )

    # ========================================================
    # RAM CAPACITY
    # ========================================================

    required_ram = requested_capacity_gb(
        request.ram
    )

    if (
        required_ram is not None
        and "RAM" in build
    ):

        actual_ram = extract_capacity_gb(
            build["RAM"]
        )

        if (
            actual_ram is not None
            and actual_ram < required_ram
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Selected RAM is only "
                    f"{actual_ram:.0f}GB, but "
                    f"{required_ram:.0f}GB was requested."
                )
            )

    # ========================================================
    # SSD CAPACITY
    # ========================================================

    required_storage = requested_capacity_gb(
        request.storage
    )

    if (
        required_storage is not None
        and "SSD" in build
    ):

        actual_storage = extract_capacity_gb(
            build["SSD"]
        )

        if (
            actual_storage is not None
            and actual_storage < required_storage
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Selected SSD is only "
                    f"{actual_storage:.0f}GB, but "
                    f"{required_storage:.0f}GB was requested."
                )
            )


# ============================================================
# API ENDPOINT
# ============================================================

@router.post("/build-pc")
def build_pc(
    request: BuildRequest
):
    start_time = time.time()

    connection = None
    cursor = None

    try:

        # ====================================================
        # DATABASE CONNECTION
        # ====================================================

        print("==========================================")
        print("PC BUILD REQUEST")
        print("==========================================")

        print("Connecting to database...")

        connection = get_connection()

        print(
            f"Database connected in "
            f"{time.time() - start_time:.2f}s"
        )

        # ====================================================
        # FETCH PRODUCTS
        # ====================================================

        cursor = connection.cursor(
            dictionary=True
        )

        print("Fetching products...")

        cursor.execute(
            """
            SELECT *
            FROM products
            """
        )

        products = cursor.fetchall()

        print(
            f"Fetched {len(products)} products in "
            f"{time.time() - start_time:.2f}s"
        )

        # ====================================================
        # CLOSE DB
        # ====================================================

        cursor.close()
        cursor = None

        connection.close()
        connection = None

        # ====================================================
        # GROUP PRODUCTS
        # ====================================================

        print("Grouping products...")

        grouped = {}

        for category, category_names in CATEGORY_FIELD_MAP.items():

            grouped[category] = [
                product
                for product in products
                if str(
                    product.get("category", "")
                ).strip()
                in category_names
            ]

            print(
                f"{category}: "
                f"{len(grouped[category])} products"
            )

        print(
            f"Products grouped in "
            f"{time.time() - start_time:.2f}s"
        )

        # ====================================================
        # GENERATE BUILD
        # ====================================================

        build = generate_local_build(
            grouped,
            request
        )

        print(
            f"Build generated in "
            f"{time.time() - start_time:.2f}s"
        )

        # ====================================================
        # VALIDATE
        # ====================================================

        validate_build(
            build,
            request
        )

        print(
            f"Build validated in "
            f"{time.time() - start_time:.2f}s"
        )

        # ====================================================
        # RESPONSE PRODUCTS
        # ====================================================

        result_products = []

        for category, product in build.items():

            item = product_to_dict(
                product
            )

            item["selected_category"] = category

            result_products.append(item)

        # ====================================================
        # TOTAL
        # ====================================================

        total_price = sum(
            safe_price(product)
            for product in build.values()
        )

        elapsed = time.time() - start_time

        print("==========================================")
        print("SUCCESS")
        print(
            f"Total price: ৳{total_price:,.0f}"
        )
        print(
            f"Budget: ৳{float(request.budget):,.0f}"
        )
        print(
            f"Total request time: "
            f"{elapsed:.2f}s"
        )
        print("==========================================")

        # ====================================================
        # API RESPONSE
        # ====================================================

        return {
            "success": True,
            "message": "PC build generated successfully.",
            "budget": float(request.budget),
            "total_price": total_price,
            "products": result_products,
        }

    # ========================================================
    # HTTP EXCEPTION
    # ========================================================

    except HTTPException:
        raise

    # ========================================================
    # GENERAL ERROR
    # ========================================================

    except Exception as e:

        print("==========================================")
        print("BUILD PC ERROR")
        print("==========================================")
        print(str(e))
        print("==========================================")

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    # ========================================================
    # FINALLY
    # ========================================================

    finally:

        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass

        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass