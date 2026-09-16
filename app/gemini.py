import os
import json

from google import genai
from pydantic import BaseModel


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

    compact_products = []

    for product in products:

        compact_products.append({
            "id": product["id"],
            "category": product["category"],
            "name": product["name"],
            "brand": product.get("brand"),
            "price": product.get("price"),
            "old_price": product.get("old_price"),
            "specifications": product.get("specifications"),
        })

    prompt = f"""
You are an AI PC Builder for a computer hardware shop.

Create ONE complete PC build using ONLY the products provided
in SHOP PRODUCTS.

USER REQUIREMENTS:

{json.dumps(requirements, ensure_ascii=False)}


SHOP PRODUCTS:

{json.dumps(compact_products, ensure_ascii=False)}


IMPORTANT RULES:

1. Select products ONLY from SHOP PRODUCTS.

2. Never invent a product.

3. Return the database ID of every selected product.

4. Create a complete PC build.

5. Consider the user's PC type.

6. Respect the user's budget as much as possible.

7. Consider the requested RAM.

8. Consider the requested storage.

9. Consider the user's priority.

10. Try to maintain reasonable hardware compatibility.

11. Prefer a balanced build.

12. Every selected product must belong to the correct category.


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


Return ONLY the required JSON structure.
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": PCBuildResponse,
        },
    )

    return PCBuildResponse.model_validate_json(response.text)