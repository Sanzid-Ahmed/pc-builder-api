import json
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .database import get_connection


router = APIRouter(
    prefix="/api/custom-build",
    tags=["Custom Build"],
)


# ============================================================
# Request Models
# ============================================================

class SaveBuildRequest(BaseModel):
    firebase_uid: str
    build_name: str
    components: dict


# ============================================================
# Database Helper
# ============================================================

def get_cursor(connection):
    return connection.cursor(dictionary=True)


# ============================================================
# Create Table
# ============================================================

def create_custom_build_table():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS custom_builds (
                id INT AUTO_INCREMENT PRIMARY KEY,

                firebase_uid VARCHAR(255) NOT NULL,

                build_name VARCHAR(255) NOT NULL,

                components JSON NOT NULL,

                created_at DATETIME NOT NULL,

                updated_at DATETIME NOT NULL
            )
            """
        )

        connection.commit()

    finally:
        cursor.close()
        connection.close()


# ============================================================
# Save Build
# ============================================================

@router.post("/save")
def save_build(request: SaveBuildRequest):

    if not request.firebase_uid.strip():
        raise HTTPException(
            status_code=400,
            detail="Firebase user ID is required.",
        )

    if not request.build_name.strip():
        raise HTTPException(
            status_code=400,
            detail="Build name is required.",
        )

    if not isinstance(request.components, dict):
        raise HTTPException(
            status_code=400,
            detail="Components must be an object.",
        )

    allowed_components = [
        "processor",
        "motherboard",
        "ram",
        "gpu",
        "storage",
        "psu",
        "case",
    ]

    cleaned_components = {}

    for component_type in allowed_components:

        product = request.components.get(
            component_type
        )

        if not product:
            cleaned_components[component_type] = None
            continue

        if not isinstance(product, dict):
            cleaned_components[component_type] = None
            continue

        product_id = product.get("id")

        if product_id is None:
            cleaned_components[component_type] = None
            continue

        cleaned_components[component_type] = {
            "id": product_id,
            "name": product.get("name"),
            "price": product.get("price"),
            "brand": product.get("brand"),
            "category": product.get("category"),
            "store": product.get("store"),
        }

    connection = get_connection()

    try:
        cursor = connection.cursor()

        now = datetime.now()

        cursor.execute(
            """
            INSERT INTO custom_builds
            (
                firebase_uid,
                build_name,
                components,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                request.firebase_uid,
                request.build_name.strip(),
                json.dumps(cleaned_components),
                now,
                now,
            ),
        )

        connection.commit()

        build_id = cursor.lastrowid

        return {
            "success": True,
            "message": "Build saved successfully.",
            "build_id": build_id,
        }

    except Exception as error:

        connection.rollback()

        print(
            "Save build error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Could not save build.",
        )

    finally:
        cursor.close()
        connection.close()


# ============================================================
# Get User Builds
# ============================================================

@router.get("/user/{firebase_uid}")
def get_user_builds(firebase_uid: str):

    if not firebase_uid.strip():
        raise HTTPException(
            status_code=400,
            detail="Firebase user ID is required.",
        )

    connection = get_connection()

    try:

        cursor = get_cursor(connection)

        cursor.execute(
            """
            SELECT
                id,
                firebase_uid,
                build_name,
                components,
                created_at,
                updated_at
            FROM custom_builds
            WHERE firebase_uid = %s
            ORDER BY updated_at DESC
            """,
            (firebase_uid,),
        )

        rows = cursor.fetchall()

        builds = []

        for row in rows:

            components = row["components"]

            if isinstance(components, str):

                try:
                    components = json.loads(
                        components
                    )

                except Exception:
                    components = {}

            builds.append(
                {
                    "id": row["id"],
                    "firebase_uid": row[
                        "firebase_uid"
                    ],
                    "build_name": row[
                        "build_name"
                    ],
                    "components": components,
                    "created_at": (
                        row["created_at"].isoformat()
                        if row["created_at"]
                        else None
                    ),
                    "updated_at": (
                        row["updated_at"].isoformat()
                        if row["updated_at"]
                        else None
                    ),
                }
            )

        return {
            "success": True,
            "count": len(builds),
            "data": builds,
        }

    except Exception as error:

        print(
            "Get builds error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Could not load builds.",
        )

    finally:
        cursor.close()
        connection.close()


# ============================================================
# Get One Build
# ============================================================

@router.get("/{build_id}")
def get_build(build_id: int):

    connection = get_connection()

    try:

        cursor = get_cursor(connection)

        cursor.execute(
            """
            SELECT
                id,
                firebase_uid,
                build_name,
                components,
                created_at,
                updated_at
            FROM custom_builds
            WHERE id = %s
            """,
            (build_id,),
        )

        row = cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Build not found.",
            )

        components = row["components"]

        if isinstance(components, str):

            try:
                components = json.loads(
                    components
                )

            except Exception:
                components = {}

        return {
            "success": True,
            "data": {
                "id": row["id"],
                "firebase_uid": row[
                    "firebase_uid"
                ],
                "build_name": row[
                    "build_name"
                ],
                "components": components,
                "created_at": (
                    row["created_at"].isoformat()
                    if row["created_at"]
                    else None
                ),
                "updated_at": (
                    row["updated_at"].isoformat()
                    if row["updated_at"]
                    else None
                ),
            },
        }

    except HTTPException:
        raise

    except Exception as error:

        print(
            "Get build error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Could not load build.",
        )

    finally:
        cursor.close()
        connection.close()


# ============================================================
# Delete Build
# ============================================================

@router.delete("/{build_id}")
def delete_build(build_id: int):

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM custom_builds
            WHERE id = %s
            """,
            (build_id,),
        )

        connection.commit()

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Build not found.",
            )

        return {
            "success": True,
            "message": "Build deleted successfully.",
        }

    except HTTPException:
        raise

    except Exception as error:

        connection.rollback()

        print(
            "Delete build error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Could not delete build.",
        )

    finally:
        cursor.close()
        connection.close()