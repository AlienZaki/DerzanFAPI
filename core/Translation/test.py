from concurrent.futures import as_completed, ThreadPoolExecutor, wait
from bson import ObjectId
from core.db import db


translation_memory_collection = db["translation_memory"]
products_collection = db["products"]

# Define a function to process each translation_memory document
def process_translation_memory(tm_document):
    source_text = tm_document["source_text"]

    # Search for products that contain the source_text in their name or description
    product_filter = {
        "$or": [
            {"name": {"$regex": source_text, "$options": "i"}},
            {"description": {"$regex": source_text, "$options": "i"}}
        ]
    }
    matching_products = products_collection.find(product_filter)

    # Get the list of matching product IDs
    matching_product_ids = [str(product["_id"]) for product in matching_products]

    print('=>', source_text, matching_product_ids)
    # Update the translation_memory document with the matching product IDs
    translation_memory_collection.update_one(
        {"_id": ObjectId(tm_document["_id"])},
        {"$set": {"products": matching_product_ids}}
    )

# Retrieve all translation_memory documents
translation_memory_documents = translation_memory_collection.find({"products": {"$exists": False}})

# Process translation_memory documents concurrently
with ThreadPoolExecutor() as executor:
    # Submit each translation_memory document for processing
    futures = [executor.submit(process_translation_memory, tm_document) for tm_document in translation_memory_documents]

    # Wait for all tasks to complete
    wait(futures)