from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests

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

@app.get("/recommend")
def recommend(productName: str, limit: int = 4):
    # Fetch all listings from NestJS backend
    try:
        response = requests.get(f"{BACKEND_URL}/listings")
        all_listings = response.json()
    except Exception as e:
        return {"error": str(e), "recommendations": []}

    # Get category of searched product
    search_category = get_category(productName)

    # Filter out the searched product and find similar ones
    recommendations = []
    for listing in all_listings:
        name = listing.get("productName", "")
        # Skip exact match
        if name.lower() == productName.lower():
            continue
        # Check same category
        if get_category(name) == search_category:
            recommendations.append({
                **listing,
                "matchReason": f"Also in {search_category} category"
            })

    # If not enough recommendations, add other active listings
    if len(recommendations) < limit:
        for listing in all_listings:
            if listing not in recommendations and listing.get("productName", "").lower() != productName.lower():
                recommendations.append({
                    **listing,
                    "matchReason": "Popular listing"
                })
            if len(recommendations) >= limit:
                break

    return {
        "searchedProduct": productName,
        "category": search_category,
        "recommendations": recommendations[:limit]
    }

@app.get("/insights/trending")
def trending_products():
    try:
        response = requests.get(f"{BACKEND_URL}/listings")
        listings = response.json()
        
        # Count products by name
        product_count = {}
        for listing in listings:
            name = listing.get("productName", "").lower()
            if name not in product_count:
                product_count[name] = {"name": name, "count": 0, "totalStock": 0}
            product_count[name]["count"] += 1
            product_count[name]["totalStock"] += listing.get("availableQuantity", 0)
        
        # Sort by count
        trending = sorted(product_count.values(), key=lambda x: x["count"], reverse=True)
        
        return {"trending": trending[:5]}
    except Exception as e:
        return {"error": str(e), "trending": []}

@app.get("/insights/missing")
def missing_products():
    try:
        response = requests.get(f"{BACKEND_URL}/listings")
        listings = response.json()
        
        # Get all listed product names
        listed = set(l.get("productName", "").lower() for l in listings)
        
        # Check which common products are missing
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
        
        # Group prices by product
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