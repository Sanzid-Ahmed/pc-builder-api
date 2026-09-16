from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .database import get_connection
from .gemini import generate_pc_build


# ==========================================
# Build PC Router
# ==========================================

router = APIRouter(
    prefix="/api",
    tags=["AI PC Builder"]
)


# ==========================================
# Request Structure
# ==========================================

class BuildRequest(BaseModel):
    type: str
    budget: float
    priority: str
    ram: str
    storage: str


# ==========================================
# Database Row → Dictionary
# ==========================================

def product_to_dict(cursor, row):

    columns = [
        column[0]
        for column in cursor.description
    ]

    product = dict(zip(columns, row))

    # Convert Decimal → float
    for key, value in product.items():

        if isinstance(value, Decimal):
            product[key] = float(value)

    return product


# ==========================================
# Required PC Categories
# ==========================================

REQUIRED_CATEGORIES = {
    "Processor",
    "Motherboard",
    "RAM",
    "RAM (Desktop)",
    "Graphics Card",
    "SSD",
    "Hard Disk Drive",
    "CPU Cooler",
    "Power Supply",
    "Casing",
}


# ==========================================
# Prepare Gemini Candidates
# ==========================================

def prepare_candidates(products, budget):

    # ------------------------------------------
    # Keep only PC Builder categories
    # ------------------------------------------

    filtered = [
        product
        for product in products
        if product.get("category") in REQUIRED_CATEGORIES
    ]

    # ------------------------------------------
    # Remove products without valid prices
    # ------------------------------------------

    filtered = [
        product
        for product in filtered
        if product.get("price") is not None
    ]

    # ------------------------------------------
    # Group products by category
    # ------------------------------------------

    grouped = {}

    for product in filtered:

        category = product["category"]

        if category not in grouped:
            grouped[category] = []

        grouped[category].append(product)

    # ------------------------------------------
    # Approximate budget distribution
    #
    # This is NOT the final build.
    # It only reduces Gemini's input size.
    # ------------------------------------------

    category_budgets = {
        "Processor": budget * 0.18,
        "Motherboard": budget * 0.12,
        "RAM": budget * 0.08,
        "RAM (Desktop)": budget * 0.08,
        "Graphics Card": budget * 0.35,
        "SSD": budget * 0.08,
        "Hard Disk Drive": budget * 0.04,
        "CPU Cooler": budget * 0.04,
        "Power Supply": budget * 0.08,
        "Casing": budget * 0.05,
    }

    candidates = []

    # ------------------------------------------
    # Select limited candidates per category
    # ------------------------------------------

    for category, category_products in grouped.items():

        target_budget = category_budgets.get(
            category,
            budget
        )

        # Sort products by distance from
        # approximate category budget
        category_products.sort(
            key=lambda product: abs(
                float(product["price"]) - target_budget
            )
        )

        # Keep only a small number
        # for Gemini
        candidates.extend(
            category_products[:15]
        )

    return candidates


# ==========================================
# AI PC Builder
# ==========================================

@router.post("/build-pc")
def build_pc(request: BuildRequest):

    connection = None
    cursor = None

    try:

        # ------------------------------------------
        # Connect to Database
        # ------------------------------------------

        connection = get_connection()
        cursor = connection.cursor()

        # ------------------------------------------
        # Get Products
        # ------------------------------------------

        cursor.execute("""
            SELECT *
            FROM products
        """)

        rows = cursor.fetchall()

        products = [
            product_to_dict(cursor, row)
            for row in rows
        ]

        if not products:

            raise HTTPException(
                status_code=404,
                detail="No products found in database"
            )

        # ------------------------------------------
        # Prepare User Requirements
        # ------------------------------------------

        requirements = {
            "type": request.type,
            "budget": request.budget,
            "priority": request.priority,
            "ram": request.ram,
            "storage": request.storage,
        }

        # ------------------------------------------
        # Reduce Product Dataset
        # ------------------------------------------

        candidates = prepare_candidates(
            products,
            request.budget
        )

        if not candidates:

            raise HTTPException(
                status_code=404,
                detail="No suitable products found"
            )

        print(
            f"Total database products: {len(products)}"
        )

        print(
            f"Products sent to Gemini: {len(candidates)}"
        )

        # ------------------------------------------
        # Ask Gemini
        # ------------------------------------------

        ai_build = generate_pc_build(
            requirements,
            candidates
        )

        # ------------------------------------------
        # Selected Product IDs
        # ------------------------------------------

        selected_ids = [
            ai_build.processor_id,
            ai_build.motherboard_id,
            ai_build.ram_id,
            ai_build.gpu_id,
            ai_build.ssd_id,
            ai_build.hdd_id,
            ai_build.cooler_id,
            ai_build.psu_id,
            ai_build.casing_id,
        ]

        # ------------------------------------------
        # Remove Duplicate IDs
        # ------------------------------------------

        selected_ids = list(
            dict.fromkeys(selected_ids)
        )

        # ------------------------------------------
        # Verify IDs
        # ------------------------------------------

        candidate_ids = {
            product["id"]
            for product in candidates
        }

        invalid_ids = [
            product_id
            for product_id in selected_ids
            if product_id not in candidate_ids
        ]

        if invalid_ids:

            raise HTTPException(
                status_code=500,
                detail=(
                    "Gemini returned invalid product IDs: "
                    f"{invalid_ids}"
                )
            )

        # ------------------------------------------
        # Get Selected Products From Database
        # ------------------------------------------

        placeholders = ",".join(
            ["%s"] * len(selected_ids)
        )

        cursor.execute(
            f"""
            SELECT *
            FROM products
            WHERE id IN ({placeholders})
            """,
            tuple(selected_ids)
        )

        selected_rows = cursor.fetchall()

        selected_products = [
            product_to_dict(cursor, row)
            for row in selected_rows
        ]

        # ------------------------------------------
        # Return Final Build
        # ------------------------------------------

        return {
            "success": True,
            "requirements": requirements,
            "build": ai_build.model_dump(),
            "products": selected_products,
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "AI PC Builder Error:",
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()