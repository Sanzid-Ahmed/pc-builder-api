# ==========================================
# Product API Routes
# ==========================================

from fastapi import APIRouter, HTTPException
from .database import get_connection


router = APIRouter(
    prefix="/api",
    tags=["Products"]
)


# ==========================================
# Convert Database Row To Dictionary
# ==========================================

def product_to_dict(row):

    return {
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
        "scraped_at": row[16].isoformat()
            if row[16] is not None else None
    }


# ==========================================
# Get All Products
# ==========================================

@router.get("/products")
def get_products(
    category: str | None = None,
    brand: str | None = None,
    store: str | None = None
):

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        # ----------------------------------
        # Base Query
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
        """

        conditions = []
        values = []


        # ----------------------------------
        # Category Filter
        # ----------------------------------

        if category:

            conditions.append("category = %s")

            values.append(category)


        # ----------------------------------
        # Brand Filter
        # ----------------------------------

        if brand:

            conditions.append("brand = %s")

            values.append(brand)


        # ----------------------------------
        # Store Filter
        # ----------------------------------

        if store:

            conditions.append("store = %s")

            values.append(store)


        # ----------------------------------
        # Add WHERE
        # ----------------------------------

        if conditions:

            query += " WHERE "

            query += " AND ".join(conditions)


        # ----------------------------------
        # Order
        # ----------------------------------

        query += " ORDER BY id ASC"


        # ----------------------------------
        # Execute
        # ----------------------------------

        cursor.execute(
            query,
            values
        )

        rows = cursor.fetchall()


        # ----------------------------------
        # Convert Results
        # ----------------------------------

        products = []

        for row in rows:

            products.append(
                product_to_dict(row)
            )


        return {
            "success": True,
            "count": len(products),
            "data": products
        }


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ==========================================
# Get Product By ID
# ==========================================

@router.get("/products/{product_id}")
def get_product(product_id: int):

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()


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
            WHERE id = %s
        """


        cursor.execute(
            query,
            (product_id,)
        )


        row = cursor.fetchone()


        if row is None:

            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )


        return {
            "success": True,
            "data": product_to_dict(row)
        }


    except HTTPException:

        raise


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ==========================================
# Get Categories
# ==========================================

@router.get("/categories")
def get_categories():

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()


        query = """
            SELECT DISTINCT category
            FROM products
            WHERE category IS NOT NULL
            ORDER BY category
        """


        cursor.execute(query)

        rows = cursor.fetchall()


        categories = [
            row[0]
            for row in rows
        ]


        return {
            "success": True,
            "count": len(categories),
            "data": categories
        }


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ==========================================
# Get Brands
# ==========================================

@router.get("/brands")
def get_brands():

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()


        query = """
            SELECT DISTINCT brand
            FROM products
            WHERE brand IS NOT NULL
            ORDER BY brand
        """


        cursor.execute(query)

        rows = cursor.fetchall()


        brands = [
            row[0]
            for row in rows
        ]


        return {
            "success": True,
            "count": len(brands),
            "data": brands
        }


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ==========================================
# Get Stores
# ==========================================

@router.get("/stores")
def get_stores():

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()


        query = """
            SELECT DISTINCT store
            FROM products
            WHERE store IS NOT NULL
            ORDER BY store
        """


        cursor.execute(query)

        rows = cursor.fetchall()


        stores = [
            row[0]
            for row in rows
        ]


        return {
            "success": True,
            "count": len(stores),
            "data": stores
        }


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ==========================================
# Health Check
# ==========================================

@router.get("/health")
def health_check():

    connection = None

    try:

        connection = get_connection()

        return {
            "success": True,
            "message": "API and database are working"
        }


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {error}"
        )


    finally:

        if connection:
            connection.close()