from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from .database import get_connection


router = APIRouter(
    prefix="/api/orders",
    tags=["Orders"]
)


# =========================================================
# REQUEST MODELS
# =========================================================

class OrderProduct(BaseModel):
    product_id: int
    product_price: float
    quantity: int


class OrderCreate(BaseModel):
    firebase_id: str
    products: List[OrderProduct]


# =========================================================
# CREATE ORDER
# =========================================================

@router.post("/")
def create_order(order: OrderCreate):

    connection = None
    cursor = None

    try:

        # -------------------------------------------------
        # 1. Basic validation
        # -------------------------------------------------

        if not order.products:
            raise HTTPException(
                status_code=400,
                detail="No products selected."
            )

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # -------------------------------------------------
        # 2. Find user using Firebase ID
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                firebase_id,
                email,
                name
            FROM users
            WHERE firebase_id = %s
            """,
            (order.firebase_id,)
        )

        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        user_id = user["id"]

        # -------------------------------------------------
        # 3. Create order
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO orders
            (
                user_id,
                user_firebase_id,
                status
            )
            VALUES (%s, %s, %s)
            """,
            (
                user_id,
                user["firebase_id"],
                "pending"
            )
        )

        order_id = cursor.lastrowid

        # -------------------------------------------------
        # 4. Add products to order
        # -------------------------------------------------

        for product in order.products:

            # ---------------------------------------------
            # Validate quantity
            # ---------------------------------------------

            if product.quantity <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Product quantity must be greater than 0."
                )

            # ---------------------------------------------
            # Validate price
            # ---------------------------------------------

            if product.product_price < 0:
                raise HTTPException(
                    status_code=400,
                    detail="Product price cannot be negative."
                )

            # ---------------------------------------------
            # Make sure product exists
            # ---------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM products
                WHERE id = %s
                """,
                (product.product_id,)
            )

            existing_product = cursor.fetchone()

            if not existing_product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product {product.product_id} not found."
                )

            # ---------------------------------------------
            # Insert order product
            # ---------------------------------------------

            cursor.execute(
                """
                INSERT INTO order_products
                (
                    order_id,
                    product_id,
                    product_price,
                    quantity
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    order_id,
                    product.product_id,
                    product.product_price,
                    product.quantity
                )
            )

        # -------------------------------------------------
        # 5. Save everything
        # -------------------------------------------------

        connection.commit()

        # -------------------------------------------------
        # 6. Calculate total quantity
        # -------------------------------------------------

        total_quantity = sum(
            product.quantity
            for product in order.products
        )

        # -------------------------------------------------
        # 7. Return result
        # -------------------------------------------------

        return {
            "success": True,
            "message": "Order created successfully.",
            "order_id": order_id,
            "status": "pending",
            "product_count": len(order.products),
            "total_quantity": total_quantity
        }

    except HTTPException:

        if connection:
            connection.rollback()

        raise

    except Exception as e:

        if connection:
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# GET USER ORDERS
# =========================================================

@router.get("/{firebase_id}")
def get_user_orders(firebase_id: str):

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # -------------------------------------------------
        # 1. Find user
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE firebase_id = %s
            """,
            (firebase_id,)
        )

        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        user_id = user["id"]

        # -------------------------------------------------
        # 2. Get orders
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                o.order_id,
                o.status,
                o.created_at,
                op.product_id,
                op.product_price,
                op.quantity,
                p.name AS product_name,
                p.images AS product_images

            FROM orders o

            JOIN order_products op
                ON o.order_id = op.order_id

            JOIN products p
                ON op.product_id = p.id

            WHERE o.user_id = %s

            ORDER BY o.created_at DESC
            """,
            (user_id,)
        )

        rows = cursor.fetchall()

        # -------------------------------------------------
        # 3. Group products by order
        # -------------------------------------------------

        orders = {}

        for row in rows:

            order_id = row["order_id"]

            if order_id not in orders:
                orders[order_id] = {
                    "order_id": order_id,
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "products": []
                }

            orders[order_id]["products"].append({
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "product_price": float(row["product_price"]),
                "quantity": row["quantity"],
                "product_images": row["product_images"]
            })

        return {
            "success": True,
            "orders": list(orders.values())
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()



# =========================================================
# GET ALL ORDERS - ADMIN
# =========================================================

@router.get("/")
def get_all_orders():

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                o.order_id,
                o.user_id,
                o.user_firebase_id,
                o.status,
                o.created_at,

                u.name AS user_name,
                u.email AS user_email,

                op.product_id,
                op.product_price,
                op.quantity,

                p.name AS product_name,
                p.images AS product_images

            FROM orders o

            JOIN users u
                ON o.user_id = u.id

            JOIN order_products op
                ON o.order_id = op.order_id

            JOIN products p
                ON op.product_id = p.id

            ORDER BY o.created_at DESC
            """
        )

        rows = cursor.fetchall()

        orders = {}

        for row in rows:

            order_id = row["order_id"]

            if order_id not in orders:

                orders[order_id] = {
                    "order_id": order_id,
                    "user_id": row["user_id"],
                    "firebase_id": row["user_firebase_id"],
                    "user_name": row["user_name"],
                    "user_email": row["user_email"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "products": [],
                    "total_price": 0
                }

            product_price = float(row["product_price"])
            quantity = row["quantity"]

            orders[order_id]["products"].append({
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "product_price": product_price,
                "quantity": quantity,
                "product_images": row["product_images"]
            })

            orders[order_id]["total_price"] += (
                product_price * quantity
            )

        return {
            "success": True,
            "orders": list(orders.values())
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()

# =========================================================
# GET SINGLE ORDER - ADMIN
# =========================================================

@router.get("/details/{order_id}")
def get_order_details(order_id: int):

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                o.order_id,
                o.user_id,
                o.user_firebase_id,
                o.status,
                o.created_at,

                u.name AS user_name,
                u.email AS user_email,

                op.product_id,
                op.product_price,
                op.quantity,

                p.name AS product_name,
                p.images AS product_images

            FROM orders o

            JOIN users u
                ON o.user_id = u.id

            JOIN order_products op
                ON o.order_id = op.order_id

            JOIN products p
                ON op.product_id = p.id

            WHERE o.order_id = %s
            """,
            (order_id,)
        )

        rows = cursor.fetchall()

        if not rows:
            raise HTTPException(
                status_code=404,
                detail="Order not found."
            )

        first_row = rows[0]

        order = {
            "order_id": first_row["order_id"],
            "user_id": first_row["user_id"],
            "firebase_id": first_row["user_firebase_id"],
            "user_name": first_row["user_name"],
            "user_email": first_row["user_email"],
            "status": first_row["status"],
            "created_at": first_row["created_at"],
            "products": [],
            "total_price": 0
        }

        for row in rows:

            product_price = float(row["product_price"])
            quantity = row["quantity"]

            order["products"].append({
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "product_price": product_price,
                "quantity": quantity,
                "product_images": row["product_images"]
            })

            order["total_price"] += (
                product_price * quantity
            )

        return {
            "success": True,
            "order": order
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# UPDATE ORDER STATUS - ADMIN
# =========================================================

class OrderStatusUpdate(BaseModel):
    status: str


@router.patch("/{order_id}/status")
def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate
):

    connection = None
    cursor = None

    try:

        allowed_statuses = [
            "pending",
            "accepted",
            "onWay",
            "complete"
        ]

        if status_update.status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail="Invalid order status."
            )

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # -------------------------------------------------
        # Check order exists
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT order_id
            FROM orders
            WHERE order_id = %s
            """,
            (order_id,)
        )

        order = cursor.fetchone()

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found."
            )

        # -------------------------------------------------
        # Update status
        # -------------------------------------------------

        cursor.execute(
            """
            UPDATE orders
            SET status = %s
            WHERE order_id = %s
            """,
            (
                status_update.status,
                order_id
            )
        )

        connection.commit()

        return {
            "success": True,
            "message": "Order status updated successfully.",
            "order_id": order_id,
            "status": status_update.status
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as e:
        if connection:
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()