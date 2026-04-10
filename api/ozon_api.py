"""
API модуль для Ozon (Official v1/review endpoints)
"""
import time
import json
import requests
from typing import List, Dict, Optional
from utils import logger

class OzonAPI:
    """Класс для работы с официальным API Ozon v1/review"""
    
    BASE_URL = "https://api-seller.ozon.ru"
    REQUEST_TIMEOUT = (5, 20)
    
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

    @staticmethod
    def _safe_json(response, request_label: str) -> Dict:
        """Безопасно парсит JSON-ответ и возвращает совместимую ошибку."""
        try:
            data = response.json()
        except ValueError as error:
            logger.error(
                f"Ozon API {request_label}: invalid JSON in HTTP {response.status_code}: {error} | body={response.text[:300]}"
            )
            return {"error": "invalid_json", "status_code": response.status_code, "details": str(error)}

        if not isinstance(data, dict):
            logger.error(
                f"Ozon API {request_label}: unexpected JSON type {type(data).__name__} in HTTP {response.status_code}"
            )
            return {
                "error": "invalid_json",
                "status_code": response.status_code,
                "details": f"unexpected json type {type(data).__name__}",
            }

        return data
    
    def _make_request(self, method: str, endpoint: str, data: dict = None, 
                      retries: int = 3, delay: float = 1.0) -> Optional[dict]:
        url = f"{self.BASE_URL}/v1/review{endpoint}"
        return self._generic_request(method, url, data, retries, delay)
    
    def _generic_request(self, method: str, url: str, data: dict = None, 
                         retries: int = 3, delay: float = 1.0) -> Optional[dict]:
        request_label = f"{method.upper()} {url}"

        for attempt in range(retries):
            try:
                if method.upper() == "POST":
                    response = self.session.post(url, json=data, timeout=self.REQUEST_TIMEOUT)
                else:
                    response = self.session.get(url, params=data, timeout=self.REQUEST_TIMEOUT)

            except requests.exceptions.Timeout as error:
                logger.error(f"Ozon API {request_label}: timeout on attempt {attempt + 1}/{retries}: {error}")
                if attempt < retries - 1:
                    time.sleep(delay * (attempt + 1))
                    continue
                return {"error": "timeout", "details": str(error)}

            except requests.exceptions.ConnectionError as error:
                logger.error(f"Ozon API {request_label}: connection error on attempt {attempt + 1}/{retries}: {error}")
                if attempt < retries - 1:
                    time.sleep(delay * (attempt + 1))
                    continue
                return {"error": "connection_error", "details": str(error)}

            except requests.exceptions.RequestException as error:
                logger.error(f"Ozon API {request_label}: request exception on attempt {attempt + 1}/{retries}: {error}")
                if attempt < retries - 1:
                    time.sleep(delay * (attempt + 1))
                    continue
                return {"error": "request_exception", "details": str(error)}

            if response.status_code == 403:
                logger.warning(f"Ozon API {request_label}: 403 antibot, attempt {attempt + 1}/{retries}")
                if attempt < retries - 1:
                    time.sleep(delay * (attempt + 1))
                    continue
                return {"error": "antibot", "status_code": 403, "details": response.text}

            if response.status_code == 429:
                logger.warning(f"Ozon API {request_label}: 429 rate limited, attempt {attempt + 1}/{retries}")
                if attempt < retries - 1:
                    time.sleep(delay * (attempt + 1))
                    continue
                return {"error": "rate_limited", "status_code": 429, "details": response.text}

            if response.status_code == 200:
                return self._safe_json(response, request_label)

            logger.error(f"Ozon API {request_label}: HTTP {response.status_code}: {response.text}")
            return {"error": response.status_code, "status_code": response.status_code, "details": response.text}
        
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
            if not isinstance(result, dict):
                logger.error(f"Ozon API: Unexpected review list response type: {type(result).__name__}")
                break

            if "error" in result:
                logger.warning(f"Ozon API: review list request failed: {result}")
                break

            reviews = result.get("reviews", [])
            logger.info(f"Ozon API: Raw UNPROCESSED reviews page: {len(reviews)}, has_next: {result.get('has_next', False)}")
            if not reviews:
                break
            
            # Enrich with info (rating, text, etc.)
            enriched = []
            for r in reviews:
                review_id = r.get("id")
                if not review_id:
                    logger.warning(f"Ozon API: Skip review without id: {r}")
                    continue

                info = self.get_review_info(review_id)
                if not isinstance(info, dict):
                    logger.warning(f"Ozon API: Invalid review info response for {review_id}: {type(info).__name__}")
                    continue
                if "error" in info:
                    logger.warning(f"Ozon API: Failed to enrich review {review_id}: {info}")
                    continue

                result_info = info.get('result', {}) or info  # Direct if no result wrapper
                if not isinstance(result_info, dict):
                    logger.warning(
                        f"Ozon API: Unexpected review info payload type for {review_id}: {type(result_info).__name__}"
                    )
                    continue

                raw_rating = result_info.get('rating')
                try:
                    rating = int(raw_rating) if raw_rating is not None else 5
                except (TypeError, ValueError):
                    logger.warning(f"Ozon API: Invalid rating for {review_id}: {raw_rating!r}, fallback to 5")
                    rating = 5

                logger.info(
                    f"{review_id}: Raw Ozon rating={raw_rating} (type={type(raw_rating)}), extracted={rating}, keys={list(result_info.keys())}"
                )
                text = result_info.get('text', '')
                logger.debug(f"Ozon API: Enriched {review_id} rating={rating} text_len={len(text)}")
                review_data = {
                    "id": review_id,
                    "review_id": review_id,
                    "rating": rating,
                    "text": text,
                    "comment": text,
                    "status": r.get("status"),
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

