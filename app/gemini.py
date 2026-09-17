import os
import json
from typing import Optional

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel

load_dotenv()


class PCBuildResponse(BaseModel):
    processor_id: int
    motherboard_id: int
    ram_id: int
    gpu_id: int
    ssd_id: int
    hdd_id: Optional[int] = None
    cooler_id: int
    psu_id: int
    casing_id: int


api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not configured")


client = genai.Client(api_key=api_key)


def generate_pc_build(
    requirements,
    products,
    validation_errors=None
):
    compact_products = []

    for product in products:
        compact_products.append({
            "id": product["id"],
            "category": product["category"],
            "name": product["name"],
            "brand": product.get("brand"),
            "price": product.get("price"),
            "status": product.get("status"),
            "features": product.get("features"),
            "specifications": product.get("specifications"),
        })

    feedback = ""

    if validation_errors:
        feedback = f"""
==========================================
PREVIOUS BUILD WAS INVALID
==========================================

The previous build failed validation.

Problems:

{json.dumps(
    validation_errors,
    ensure_ascii=False,
    indent=2
)}

Fix EVERY problem.

Generate a completely NEW build.
Do not repeat the invalid selection.
"""

    prompt = f"""
You are an expert AI PC Builder for a computer
hardware shop.

Create ONE realistic PC build using ONLY products
from SHOP PRODUCTS.

==========================================
USER REQUIREMENTS
==========================================

{json.dumps(
    requirements,
    ensure_ascii=False,
    indent=2
)}

==========================================
SHOP PRODUCTS
==========================================

{json.dumps(
    compact_products,
    ensure_ascii=False
)}

{feedback}

==========================================
MANDATORY RULES
==========================================

1. Use ONLY products from SHOP PRODUCTS.

2. Never invent products.

3. Every selected ID must exactly match an
   existing product ID.

4. Never return 0.

5. Never return a fake ID.

6. Never return duplicate IDs.

7. Every required component must have exactly
   ONE product.

8. HDD IS OPTIONAL.

9. Do NOT select an HDD when the user's storage
   requirement only asks for an SSD.

10. Select an HDD ONLY when:
    - the user explicitly requests HDD, OR
    - the user requests additional/multiple storage.

11. If HDD is not required, return:
    "hdd_id": null

12. SSD must belong to category:
    "SSD"

13. HDD must belong to category:
    "Hard Disk Drive"

14. RAM must belong to:
    "RAM"
    OR
    "RAM (Desktop)"

15. Processor must belong to:
    "Processor"

16. Motherboard must belong to:
    "Motherboard"

17. GPU must belong to:
    "Graphics Card"

18. CPU cooler must belong to:
    "CPU Cooler"

19. PSU must belong to:
    "Power Supply"

20. Casing must belong to:
    "Casing"

21. Prefer products marked "In Stock".

22. Avoid:
    - Out of Stock
    - Up Coming
    - Upcoming
    - Coming Soon
    - Discontinued

23. However, if no suitable in-stock product
    exists for a required category, use the best
    available product from that category.

24. The final build MUST NOT exceed the user's
    maximum budget.

25. Never waste a large part of the budget on
    unnecessary storage.

26. For GAMING builds:
    - prioritize GPU performance
    - then CPU performance
    - maintain reasonable motherboard,
      RAM, PSU and cooling
    - avoid extremely old CPUs/GPUs when better
      candidates are available

27. For AI & ML builds:
    prioritize GPU capability and CPU/RAM.

28. For Professional builds:
    prioritize CPU, RAM, reliability and storage.

29. For Content Creation:
    prioritize CPU, GPU, RAM and storage.

30. For General builds:
    prioritize balanced value.

31. Respect the requested RAM capacity.

32. Respect the requested SSD/storage capacity.

33. Processor and motherboard must be compatible.

34. Motherboard and RAM must be compatible.

35. PSU must be appropriate for the CPU/GPU.

36. Prefer a balanced build rather than simply
    choosing the cheapest product.

37. Do NOT choose a very expensive product merely
    because the user's budget is high.

38. Use the budget efficiently.

39. Calculate the total price before returning.

40. Total price MUST NOT exceed the maximum budget.

==========================================
REQUIRED COMPONENTS
==========================================

Processor
Motherboard
RAM
Graphics Card
SSD
CPU Cooler
Power Supply
Casing

OPTIONAL:
Hard Disk Drive

==========================================
FINAL CHECK
==========================================

Before returning JSON, verify:

- Every ID exists.
- Every ID is positive.
- No duplicate IDs.
- Correct category.
- RAM requirement satisfied.
- SSD requirement satisfied.
- HDD only if requested.
- Total within budget.
- CPU and motherboard compatible.
- Motherboard and RAM compatible.
- PSU suitable.
- Build matches PC type.
- Build matches priority.

Return ONLY JSON.

The JSON must contain:

processor_id
motherboard_id
ram_id
gpu_id
ssd_id
hdd_id
cooler_id
psu_id
casing_id

If HDD is unnecessary:
"hdd_id": null
"""

    response = client.interactions.create(
        model="gemini-3.6-flash",
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": PCBuildResponse.model_json_schema(),
        },
    )

    print("------------------------------------------")
    print("GEMINI RAW RESPONSE:")
    print(response.output_text)
    print("------------------------------------------")

    return PCBuildResponse.model_validate_json(
        response.output_text
    )