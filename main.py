from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BACKEND_URL = "http://localhost:5000"

CATEGORIES = {
    "grains": ["rice", "wheat", "corn", "maize", "barley", "oats", "millet"],
    "vegetables": ["tomato", "potato", "carrot", "onion", "garlic", "spinach", "cabbage", "lettuce"],
    "fruits": ["apple", "banana", "mango", "orange", "grape", "strawberry", "watermelon"],
    "legumes": ["beans", "lentils", "peas", "chickpeas", "soybean"],
    "herbs": ["basil", "parsley", "mint", "coriander", "thyme"],
    "dairy": ["milk", "cheese", "butter", "yogurt"],
    "roots": ["ginger", "turmeric", "radish", "beetroot"],
}

def get_category(product_name: str):
    name = product_name.lower()
    for category, keywords in CATEGORIES.items():
        if any(keyword in name for keyword in keywords):
            return category
    return "other"

def build_product_description(listing):
    """Build a rich text description for TF-IDF vectorization"""
    name = listing.get("productName", "").lower()
    category = get_category(name)
    unit = listing.get("unit", "")
    # Repeat category and name to give them more weight
    return f"{name} {name} {category} {category} {unit}"

def get_tfidf_recommendations(query: str, listings: list, limit: int = 4):
    """Use TF-IDF + Cosine Similarity to find similar products"""
    if not listings:
        return []

    # Build descriptions for all listings
    descriptions = [build_product_description(l) for l in listings]
    
    # Add the query to the list for vectorization
    query_category = get_category(query)
    query_description = f"{query.lower()} {query.lower()} {query_category} {query_category}"
    all_descriptions = [query_description] + descriptions

    # Apply TF-IDF Vectorization
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(all_descriptions)

    # Calculate Cosine Similarity between query and all listings
    query_vector = tfidf_matrix[0]
    listing_vectors = tfidf_matrix[1:]
    similarities = cosine_similarity(query_vector, listing_vectors)[0]

    # Sort by similarity score
    scored = []
    for i, (listing, score) in enumerate(zip(listings, similarities)):
        if listing.get("productName", "").lower() != query.lower():
            scored.append({
                **listing,
                "similarityScore": round(float(score), 4),
                "matchReason": f"TF-IDF similarity: {round(float(score) * 100, 1)}%"
            })

    # Sort by similarity score descending
    scored.sort(key=lambda x: x["similarityScore"], reverse=True)
    return scored[:limit]


@app.get("/recommend")
def recommend(productName: str, limit: int = 4):
    try:
        response = requests.get(f"{BACKEND_URL}/listings")
        all_listings = response.json()
    except Exception as e:
        return {"error": str(e), "recommendations": []}

    recommendations = get_tfidf_recommendations(productName, all_listings, limit)

    return {
        "searchedProduct": productName,
        "category": get_category(productName),
        "algorithm": "TF-IDF + Cosine Similarity",
        "recommendations": recommendations
    }


@app.get("/insights/trending")
def trending_products():
    try:
        response = requests.get(f"{BACKEND_URL}/listings")
        listings = response.json()

        product_count = {}
        for listing in listings:
            name = listing.get("productName", "").lower()
            if name not in product_count:
                product_count[name] = {"name": name, "count": 0, "totalStock": 0}
            product_count[name]["count"] += 1
            product_count[name]["totalStock"] += listing.get("availableQuantity", 0)

        trending = sorted(product_count.values(), key=lambda x: x["count"], reverse=True)
        return {"trending": trending[:5]}
    except Exception as e:
        return {"error": str(e), "trending": []}


@app.get("/insights/missing")
def missing_products():
    try:
        response = requests.get(f"{BACKEND_URL}/listings")
        listings = response.json()

        listed = set(l.get("productName", "").lower() for l in listings)

        all_common = []
        for category, products in CATEGORIES.items():
            for product in products:
                if product not in listed:
                    all_common.append({"product": product, "category": category})

        return {"missing": all_common[:8]}
    except Exception as e:
        return {"error": str(e), "missing": []}


@app.get("/insights/pricing")
def pricing_suggestions():
    try:
        response = requests.get(f"{BACKEND_URL}/listings")
        listings = response.json()

        product_prices = {}
        for listing in listings:
            name = listing.get("productName", "").lower()
            price = listing.get("currentPrice")
            if price and name:
                if name not in product_prices:
                    product_prices[name] = []
                product_prices[name].append(price)

        suggestions = []
        for product, prices in product_prices.items():
            avg = sum(prices) / len(prices)
            suggestions.append({
                "product": product,
                "averagePrice": round(avg, 2),
                "minPrice": min(prices),
                "maxPrice": max(prices),
                "suggestion": f"Market average is ${avg:.2f}. {'Consider raising price.' if min(prices) < avg * 0.8 else 'Your price is competitive.'}"
            })

        return {"suggestions": suggestions}
    except Exception as e:
        return {"error": str(e), "suggestions": []}


@app.get("/insights/seasonal")
def seasonal_crops():
    from datetime import datetime
    month = datetime.now().month

    seasonal = {
        "summer": ["tomato", "corn", "watermelon", "mango", "cucumber"],
        "autumn": ["apple", "potato", "pumpkin", "grape", "carrot"],
        "winter": ["cabbage", "spinach", "lettuce", "broccoli", "cauliflower"],
        "spring": ["strawberry", "peas", "asparagus", "radish", "beetroot"],
    }

    if month in [12, 1, 2]:
        season = "summer"
    elif month in [3, 4, 5]:
        season = "autumn"
    elif month in [6, 7, 8]:
        season = "winter"
    else:
        season = "spring"

    return {
        "currentSeason": season,
        "recommendedCrops": seasonal[season],
        "month": month
    }


@app.get("/health")
def health():
    return {"status": "ok"}