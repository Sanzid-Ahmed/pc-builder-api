from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from .database import get_connection


router = APIRouter(
    prefix="/api/build-limit",
    tags=["Build Limit"]
)


# =========================================================
# REQUEST MODELS
# =========================================================

class UpdateBuildLimit(BaseModel):
    build_limit: Optional[int] = Field(
        default=None,
        ge=0
    )


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_user_by_firebase_id(cursor, firebase_id: str):
    cursor.execute(
        """
        SELECT
            id,
            firebase_id,
            email,
            name,
            role,
            build_limit
        FROM users
        WHERE firebase_id = %s
        """,
        (firebase_id,)
    )

    return cursor.fetchone()


def require_admin(cursor, admin_firebase_id: str):
    admin = get_user_by_firebase_id(
        cursor,
        admin_firebase_id
    )

    if not admin:
        raise HTTPException(
            status_code=404,
            detail="Admin user not found."
        )

    if admin["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can perform this action."
        )

    return admin


# =========================================================
# GET OWN BUILD LIMIT
# =========================================================

@router.get("/{firebase_id}")
def get_build_limit(firebase_id: str):

    connection = None
    cursor = None

    try:

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        user = get_user_by_firebase_id(
            cursor,
            firebase_id
        )

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        # Admin = unlimited
        if user["role"] == "admin":

            return {
                "success": True,
                "firebase_id": user["firebase_id"],
                "name": user["name"],
                "role": "admin",
                "build_limit": None,
                "unlimited": True
            }

        return {
            "success": True,
            "firebase_id": user["firebase_id"],
            "name": user["name"],
            "role": "user",
            "build_limit": user["build_limit"],
            "unlimited": False
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
# ADMIN GET ANY USER BUILD LIMIT
# =========================================================

@router.get("/admin/{admin_firebase_id}/user/{user_firebase_id}")
def admin_get_user_build_limit(
    admin_firebase_id: str,
    user_firebase_id: str
):

    connection = None
    cursor = None

    try:

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # Check requester
        require_admin(
            cursor,
            admin_firebase_id
        )

        # Get target user
        target_user = get_user_by_firebase_id(
            cursor,
            user_firebase_id
        )

        if not target_user:
            raise HTTPException(
                status_code=404,
                detail="Target user not found."
            )

        # Admin target = unlimited
        if target_user["role"] == "admin":

            return {
                "success": True,
                "user": {
                    "id": target_user["id"],
                    "firebase_id": target_user["firebase_id"],
                    "email": target_user["email"],
                    "name": target_user["name"],
                    "role": "admin",
                    "build_limit": None,
                    "unlimited": True
                }
            }

        return {
            "success": True,
            "user": {
                "id": target_user["id"],
                "firebase_id": target_user["firebase_id"],
                "email": target_user["email"],
                "name": target_user["name"],
                "role": "user",
                "build_limit": target_user["build_limit"],
                "unlimited": False
            }
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
# ADMIN GET ALL USER BUILD LIMITS
# =========================================================

@router.get("/admin/{admin_firebase_id}/users")
def admin_get_all_build_limits(
    admin_firebase_id: str
):

    connection = None
    cursor = None

    try:

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # Check requester
        require_admin(
            cursor,
            admin_firebase_id
        )

        cursor.execute(
            """
            SELECT
                id,
                firebase_id,
                email,
                name,
                role,
                build_limit
            FROM users
            ORDER BY id DESC
            """
        )

        users = cursor.fetchall()

        formatted_users = []

        for user in users:

            if user["role"] == "admin":

                user["build_limit"] = None
                user["unlimited"] = True

            else:

                user["unlimited"] = False

            formatted_users.append(user)

        return {
            "success": True,
            "count": len(formatted_users),
            "users": formatted_users
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
# ADMIN UPDATE ANY USER BUILD LIMIT
# =========================================================

@router.put("/admin/{admin_firebase_id}/user/{user_firebase_id}")
def admin_update_build_limit(
    admin_firebase_id: str,
    user_firebase_id: str,
    data: UpdateBuildLimit
):

    connection = None
    cursor = None

    try:

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # =================================================
        # 1. CHECK ADMIN
        # =================================================

        require_admin(
            cursor,
            admin_firebase_id
        )

        # =================================================
        # 2. GET TARGET USER
        # =================================================

        target_user = get_user_by_firebase_id(
            cursor,
            user_firebase_id
        )

        if not target_user:
            raise HTTPException(
                status_code=404,
                detail="Target user not found."
            )

        # =================================================
        # 3. DON'T MODIFY ADMIN LIMIT
        # =================================================

        if target_user["role"] == "admin":

            raise HTTPException(
                status_code=400,
                detail="Admin users have unlimited builds. Their build limit cannot be changed."
            )

        # =================================================
        # 4. UPDATE LIMIT
        # =================================================

        cursor.execute(
            """
            UPDATE users
            SET build_limit = %s
            WHERE firebase_id = %s
            """,
            (
                data.build_limit,
                user_firebase_id
            )
        )

        connection.commit()

        # =================================================
        # 5. GET UPDATED USER
        # =================================================

        cursor.execute(
            """
            SELECT
                id,
                firebase_id,
                email,
                name,
                role,
                build_limit
            FROM users
            WHERE firebase_id = %s
            """,
            (user_firebase_id,)
        )

        updated_user = cursor.fetchone()

        return {
            "success": True,
            "message": "Build limit updated successfully.",
            "user": updated_user
        }

    except HTTPException:
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
# USE ONE BUILD
# =========================================================

@router.post("/{firebase_id}/use")
def use_build(firebase_id: str):

    connection = None
    cursor = None

    try:

        connection = get_connection()

        # Important for transaction
        cursor = connection.cursor(dictionary=True)

        # Lock user's row
        cursor.execute(
            """
            SELECT
                id,
                firebase_id,
                role,
                build_limit
            FROM users
            WHERE firebase_id = %s
            FOR UPDATE
            """,
            (firebase_id,)
        )

        user = cursor.fetchone()

        if not user:

            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        # =================================================
        # ADMIN = UNLIMITED
        # =================================================

        if user["role"] == "admin":

            connection.commit()

            return {
                "success": True,
                "message": "Admin has unlimited builds.",
                "role": "admin",
                "build_limit": None,
                "unlimited": True
            }

        # =================================================
        # USER LIMIT CHECK
        # =================================================

        current_limit = user["build_limit"]

        if current_limit is None:

            current_limit = 10

        if current_limit <= 0:

            connection.rollback()

            raise HTTPException(
                status_code=403,
                detail="You have reached your build limit."
            )

        # =================================================
        # DECREASE LIMIT
        # =================================================

        new_limit = current_limit - 1

        cursor.execute(
            """
            UPDATE users
            SET build_limit = %s
            WHERE firebase_id = %s
            """,
            (
                new_limit,
                firebase_id
            )
        )

        connection.commit()

        return {
            "success": True,
            "message": "Build used successfully.",
            "role": "user",
            "build_limit": new_limit,
            "unlimited": False
        }

    except HTTPException:
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
# ADMIN RESET USER LIMIT
# =========================================================

@router.post("/admin/{admin_firebase_id}/user/{user_firebase_id}/reset")
def admin_reset_build_limit(
    admin_firebase_id: str,
    user_firebase_id: str
):

    connection = None
    cursor = None

    try:

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # Check admin
        require_admin(
            cursor,
            admin_firebase_id
        )

        # Get target user
        target_user = get_user_by_firebase_id(
            cursor,
            user_firebase_id
        )

        if not target_user:

            raise HTTPException(
                status_code=404,
                detail="Target user not found."
            )

        # Admin is already unlimited
        if target_user["role"] == "admin":

            raise HTTPException(
                status_code=400,
                detail="Admin users already have unlimited builds."
            )

        # Reset to 10
        cursor.execute(
            """
            UPDATE users
            SET build_limit = 10
            WHERE firebase_id = %s
            """,
            (user_firebase_id,)
        )

        connection.commit()

        return {
            "success": True,
            "message": "Build limit reset successfully.",
            "firebase_id": user_firebase_id,
            "build_limit": 10
        }

    except HTTPException:
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