# ==========================================
# AI PC Builder Routes
# ==========================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .database import get_connection
from .gemini import generate_pc_build


router = APIRouter(
    prefix="/api",
    tags=["AI PC Builder"]
)


# ==========================================
# Request Models
# ==========================================

class BuildRequirements(BaseModel):
    type: str
    budget: str
    priority: str
    ram: str
    storage: str


class BuildRequest(BaseModel):
    requirements: BuildRequirements


# ==========================================
# AI PC Builder
# ==========================================

@router.post("/build-pc")
def build_pc(request: BuildRequest):

    connection = None
    cursor = None

    try:

        # ----------------------------------
        # Connect to Database
        # ----------------------------------

        connection = get_connection()
        cursor = connection.cursor()

        # ----------------------------------
        # Get Products
        # ----------------------------------

        query = """
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
                specifications,
                scraped_at
            FROM products
            ORDER BY id ASC
        """

        cursor.execute(query)

        rows = cursor.fetchall()

        # ----------------------------------
        # Convert Database Rows
        # ----------------------------------

        products = []

        for row in rows:

            products.append({
                "id": row[0],
                "store": row[1],
                "name": row[2],
                "category": row[3],
                "brand": row[4],
                "product_code": row[5],
                "price": float(row[6]) if row[6] is not None else None,
                "old_price": float(row[7]) if row[7] is not None else None,
                "status": row[8],
                "warranty": row[9],
                "rating": float(row[10]) if row[10] is not None else None,
                "reviews": row[11],
                "url": row[12],
                "images": row[13],
                "features": row[14],
                "specifications": row[15],
                "scraped_at": (
                    row[16].isoformat()
                    if row[16] is not None
                    else None
                )
            })

        if not products:

            raise HTTPException(
                status_code=404,
                detail="No products available"
            )

        # ----------------------------------
        # Generate AI Build
        # ----------------------------------

        ai_build = generate_pc_build(
            request.requirements.model_dump(),
            products
        )

        # ----------------------------------
        # Selected Product IDs
        # ----------------------------------

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

        # ----------------------------------
        # Get Actual Products
        # ----------------------------------

        selected_products = [
            product
            for product in products
            if product["id"] in selected_ids
        ]

        # ----------------------------------
        # Return Result
        # ----------------------------------

        return {
            "success": True,
            "data": {
                "build": ai_build.model_dump(),
                "products": selected_products
            }
        }

    except HTTPException:
        raise

    except Exception as error:

        print("AI BUILD ERROR:", error)

        raise HTTPException(
            status_code=500,
            detail=f"AI PC Builder failed: {error}"
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()