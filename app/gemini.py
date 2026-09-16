import os
import json

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel


# ==========================================
# Load Environment Variables
# ==========================================

load_dotenv()


# ==========================================
# Gemini Response Structure
# ==========================================

class PCBuildResponse(BaseModel):
    processor_id: int
    motherboard_id: int
    ram_id: int
    gpu_id: int
    ssd_id: int
    hdd_id: int
    cooler_id: int
    psu_id: int
    casing_id: int


# ==========================================
# Gemini Client
# ==========================================

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not configured")

client = genai.Client(api_key=api_key)


# ==========================================
# Generate PC Build
# ==========================================

def generate_pc_build(requirements, products):

    # ------------------------------------------
    # Make Product Data Small
    # ------------------------------------------

    compact_products = []

    for product in products:

        compact_products.append({
            "id": product["id"],
            "category": product["category"],
            "name": product["name"],
            "brand": product.get("brand"),
            "price": product.get("price"),
        })

    # ------------------------------------------
    # Create Prompt
    # ------------------------------------------

    prompt = f"""
You are an AI PC Builder for a computer hardware shop.

Your job is to create ONE complete PC build using ONLY the
products provided in SHOP PRODUCTS.

USER REQUIREMENTS:

{json.dumps(requirements, ensure_ascii=False)}


SHOP PRODUCTS:

{json.dumps(compact_products, ensure_ascii=False)}


IMPORTANT RULES:

1. Select products ONLY from SHOP PRODUCTS.
2. Never invent a product.
3. Return the database ID of every selected product.
4. Every selected ID MUST exist in SHOP PRODUCTS.
5. Every component must belong to the correct category.
6. Respect the user's budget as much as possible.
7. Consider the user's PC type.
8. Consider the user's priority.
9. Consider the requested RAM.
10. Consider the requested storage.
11. Try to maintain reasonable hardware compatibility.
12. Prefer a balanced build.
13. Do not explain your answer.
14. Return ONLY the required JSON structure.

REQUIRED COMPONENTS:

Processor
Motherboard
RAM
Graphics Card
SSD
Hard Disk Drive
CPU Cooler
Power Supply
Casing
"""

    # ------------------------------------------
    # Ask Gemini
    # ------------------------------------------

    response = client.interactions.create(
        model="gemini-3.6-flash",
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": PCBuildResponse.model_json_schema(),
        },
    )

    # ------------------------------------------
    # Parse Gemini Response
    # ------------------------------------------

    return PCBuildResponse.model_validate_json(
        response.output_text
    )