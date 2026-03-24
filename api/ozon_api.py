"""
API модуль для Ozon (Official v1/review endpoints)
"""
import time
import requests
import json
from typing import List, Dict, Optional
from utils import logger
from datetime import datetime, timedelta

# Add class var for debug



class OzonAPI:
    """Класс для работы с официальным API Ozon v1/review"""
    
    BASE_URL = "https://api-seller.ozon.ru"
    
    def __init__(self, api_key: str, company_id: str):
        self.api_key = api_key
        self.company_id = company_id
        self.session = requests.Session()
        self.session.headers.update({
            "Client-Id": company_id,
            "Api-Key": api_key,
            "Content-Type": "application/json"
        })
        self._debug_review_logged = False  # Log first full review info only

    
    def _make_request(self, method: str, endpoint: str, data: dict = None, 
                      retries: int = 3, delay: float = 1.0) -> Optional[dict]:
        url = f"{self.BASE_URL}/v1/review{endpoint}"
        return self._generic_request(method, url, data, retries, delay)
    
    def _generic_request(self, method: str, url: str, data: dict = None, 
                         retries: int = 3, delay: float = 1.0) -> Optional[dict]:
        for attempt in range(retries):
            try:
                if method.upper() == "POST":
                    response = self.session.post(url, json=data)
                else:
                    response = self.session.get(url, params=data)
                
                if response.status_code == 403:
                    logger.warning(f"Ozon API: 403 antibot, attempt {attempt + 1}/{retries}")
                    if attempt < retries - 1:
                        time.sleep(delay * (attempt + 1))
                        continue
                    return {"error": "antibot", "details": response.text}
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Ozon API: {response.status_code}: {response.text}")
                    return {"error": response.status_code, "details": response.text}
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Ozon API request exception: {e}")
                if attempt < retries - 1:
                    time.sleep(delay * (attempt + 1))
                    continue
                return {"error": "exception", "details": str(e)}
        
        return {"error": "max_retries"}
    
    def get_review_list(self, status: str = "UNPROCESSED", limit: int = 100, last_id: str = None, sort_dir: str = "ASC") -> Dict:
        """ /v1/review/list - Get list of reviews (paginated) """
        data = {
            "status": status,
            "limit": limit,
            "sort_dir": sort_dir
        }
        if last_id:
            data["last_id"] = last_id
        return self._make_request("POST", "/list", data)
    
    def get_review_info(self, review_id: str) -> Dict:
        """ /v1/review/info - Get detailed review info """
        data = {"review_id": review_id}
        result = self._make_request("POST", "/info", data)
        
        # Log full response for first call to diagnose structure
        if result and not self._debug_review_logged:
            logger.info(f"Ozon API DEBUG FULL REVIEW INFO for {review_id}: {json.dumps(result, ensure_ascii=False, indent=2)}")
            self._debug_review_logged = True
        
        return result

    
    def send_comment(self, review_id: str, text: str, mark_processed: bool = True, parent_comment_id: str = None) -> bool:
        """ /v1/review/comment/create - Send comment (answer) to review """
        data = {
            "review_id": review_id,
            "text": text,
            "mark_review_as_processed": mark_processed
        }
        if parent_comment_id:
            data["parent_comment_id"] = parent_comment_id
        
        result = self._make_request("POST", "/comment/create", data)
        
        if result and "error" not in result:
            logger.info(f"Ozon API: Comment sent to review {review_id}, ID: {result.get('comment_id')}")
            return True
        logger.error(f"Ozon API: Failed to send comment to {review_id}: {result}")
        return False
    
    def get_unanswered_reviews(self, since_days: int = 30, min_rating: int = 1) -> List[Dict]:
        """Get unanswered (UNPROCESSED) reviews, enriched with info """
        all_reviews = []
        last_id = None
        
        while True:
            result = self.get_review_list("UNPROCESSED", limit=100, last_id=last_id)
            logger.info(f"Ozon API: Raw UNPROCESSED page: {len(result.get('reviews', []))}, has_next: {result.get('has_next', False)}")
            if "error" in result or not result:
                break
            
            reviews = result.get("reviews", [])
            logger.info(f"Ozon API: Raw UNPROCESSED reviews page: {len(reviews)}, has_next: {result.get('has_next', False)}")
            if not reviews:
                break
            
            # Enrich with info (rating, text, etc.)
            enriched = []
            for r in reviews:
                info = self.get_review_info(r["id"])
                if "error" not in info:
                    result_info = info.get('result', {}) or info  # Direct if no result wrapper
                    raw_rating = result_info.get('rating')
                    rating = int(raw_rating) if raw_rating is not None else 5
                    logger.info(f"{r['id']}: Raw Ozon rating={raw_rating} (type={type(raw_rating)}), extracted={rating}, keys={list(result_info.keys())}")
                    text = result_info.get('text', '')
                    logger.debug(f"Ozon API: Enriched {r['id']} rating={rating} text_len={len(text)}")
                    review_data = {
                        "id": r["id"],
                        "review_id": r["id"],
                        "rating": rating,
                        "text": text,
                        "comment": text,
                        "status": r["status"],
                        "published_at": r.get("published_at"),
                        "answer": None  # Unprocessed
                    }
                    if rating >= min_rating:
                        enriched.append(review_data)
            
            all_reviews.extend(enriched)
            
            if not result.get("has_next", False):
                break
            
            last_id = result.get("last_id")
            time.sleep(1.0)  # Increase to avoid rate limit
        
        logger.info(f"Ozon API: Processed {len(all_reviews)} unanswered reviews after enrichment (min_rating={min_rating})")
        if not all_reviews:
            logger.warning("Ozon API: No reviews after rating filter - check API response structure in logs")
        return all_reviews
    
    def get_review_count(self) -> Dict:
        """ /v1/review/count - Get review counts """
        return self._make_request("POST", "/count", {})


# Backward compatibility methods (deprecated)
def get_product_reviews(self, limit: int = 20, offset: int = 0) -> List[Dict]:
    logger.warning("get_product_reviews DEPRECATED - use get_review_list")
    return []

def get_all_reviews(self, since_days: int = 30, limit_per_request: int = 200) -> List[Dict]:
    logger.warning("get_all_reviews DEPRECATED")
    return []

OzonAPI.get_product_reviews = get_product_reviews
OzonAPI.get_all_reviews = get_all_reviews
OzonAPI.send_answer = OzonAPI.send_comment

