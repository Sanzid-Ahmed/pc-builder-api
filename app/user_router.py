from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from .database import get_connection


router = APIRouter(
    prefix="/api/users",
    tags=["Users"]
)


# =========================================================
# REQUEST MODELS
# =========================================================

class UserCreate(BaseModel):
    firebase_id: str
    email: str
    name: str
    role: str


class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None


# =========================================================
# HELPER
# =========================================================

def get_build_limit(role: str):
    """
    Normal user = 10 builds
    Admin = unlimited (NULL)
    """

    if role == "user":
        return 10

    if role == "admin":
        return None

    raise HTTPException(
        status_code=400,
        detail="Role must be either 'user' or 'admin'."
    )


# =========================================================
# CREATE / SYNC USER
# =========================================================

@router.post("/sync")
def create_or_get_user(user: UserCreate):

    if user.role not in ["user", "admin"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid role. Role must be 'user' or 'admin'."
        )

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(dictionary=True)

        # -------------------------------------------------
        # 1. Check Firebase ID
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                firebase_id,
                email,
                name,
                role,
                build_limit,
                created_at
            FROM users
            WHERE firebase_id = %s
            """,
            (user.firebase_id,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            return {
                "success": True,
                "created": False,
                "message": "User already exists.",
                "user": existing_user
            }

        # -------------------------------------------------
        # 2. Check Email
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                firebase_id,
                email,
                name,
                role,
                build_limit,
                created_at
            FROM users
            WHERE email = %s
            """,
            (user.email,)
        )

        existing_email = cursor.fetchone()

        if existing_email:

            return {
                "success": True,
                "created": False,
                "message": "A user with this email already exists.",
                "user": existing_email
            }

        # -------------------------------------------------
        # 3. Determine build limit
        # -------------------------------------------------

        build_limit = get_build_limit(user.role)

        # -------------------------------------------------
        # 4. Create user
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO users
            (
                firebase_id,
                email,
                name,
                role,
                build_limit
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                user.firebase_id,
                user.email,
                user.name,
                user.role,
                build_limit
            )
        )

        connection.commit()

        # -------------------------------------------------
        # 5. Get newly created user
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                firebase_id,
                email,
                name,
                role,
                build_limit,
                created_at
            FROM users
            WHERE firebase_id = %s
            """,
            (user.firebase_id,)
        )

        new_user = cursor.fetchone()

        return {
            "success": True,
            "created": True,
            "message": "User created successfully.",
            "user": new_user
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
# GET ALL USERS
# =========================================================

@router.get("/")
def get_all_users():

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                firebase_id,
                email,
                name,
                role,
                build_limit,
                created_at
            FROM users
            ORDER BY id DESC
            """
        )

        users = cursor.fetchall()

        return {
            "success": True,
            "count": len(users),
            "users": users
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
# GET USER BY DATABASE ID
# =========================================================

@router.get("/id/{user_id}")
def get_user_by_id(user_id: int):

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                firebase_id,
                email,
                name,
                role,
                build_limit,
                created_at
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        user = cursor.fetchone()

        if not user:

            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        return {
            "success": True,
            "user": user
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
# GET USER BY FIREBASE ID
# =========================================================

@router.get("/firebase/{firebase_id}")
def get_user_by_firebase_id(firebase_id: str):

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                firebase_id,
                email,
                name,
                role,
                build_limit,
                created_at
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

        return {
            "success": True,
            "user": user
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
# UPDATE USER
# =========================================================

@router.put("/{user_id}")
def update_user(
    user_id: int,
    user: UserUpdate
):

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(dictionary=True)

        # -------------------------------------------------
        # 1. Check existing user
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                firebase_id,
                email,
                name,
                role,
                build_limit,
                created_at
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        existing_user = cursor.fetchone()

        if not existing_user:

            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        # -------------------------------------------------
        # 2. Prepare new values
        # -------------------------------------------------

        new_email = (
            user.email
            if user.email is not None
            else existing_user["email"]
        )

        new_name = (
            user.name
            if user.name is not None
            else existing_user["name"]
        )

        new_role = (
            user.role
            if user.role is not None
            else existing_user["role"]
        )

        # -------------------------------------------------
        # 3. Validate role
        # -------------------------------------------------

        if new_role not in ["user", "admin"]:

            raise HTTPException(
                status_code=400,
                detail="Role must be either 'user' or 'admin'."
            )

        # -------------------------------------------------
        # 4. Check duplicate email
        # -------------------------------------------------

        if new_email != existing_user["email"]:

            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE email = %s
                AND id != %s
                """,
                (new_email, user_id)
            )

            duplicate_email = cursor.fetchone()

            if duplicate_email:

                raise HTTPException(
                    status_code=409,
                    detail="Another user already uses this email."
                )

        # -------------------------------------------------
        # 5. Determine build limit
        # -------------------------------------------------

        new_build_limit = get_build_limit(new_role)

        # -------------------------------------------------
        # 6. Update
        # -------------------------------------------------

        cursor.execute(
            """
            UPDATE users
            SET
                email = %s,
                name = %s,
                role = %s,
                build_limit = %s
            WHERE id = %s
            """,
            (
                new_email,
                new_name,
                new_role,
                new_build_limit,
                user_id
            )
        )

        connection.commit()

        # -------------------------------------------------
        # 7. Get updated user
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                firebase_id,
                email,
                name,
                role,
                build_limit,
                created_at
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        updated_user = cursor.fetchone()

        return {
            "success": True,
            "message": "User updated successfully.",
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
# DELETE USER
# =========================================================

@router.delete("/{user_id}")
def delete_user(user_id: int):

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(dictionary=True)

        # -------------------------------------------------
        # 1. Check user
        # -------------------------------------------------

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
            WHERE id = %s
            """,
            (user_id,)
        )

        user = cursor.fetchone()

        if not user:

            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        # -------------------------------------------------
        # 2. Delete
        # -------------------------------------------------

        cursor.execute(
            """
            DELETE FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        connection.commit()

        return {
            "success": True,
            "message": "User deleted successfully.",
            "deleted_user": user
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