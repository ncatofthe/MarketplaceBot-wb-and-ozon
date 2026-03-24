"""
API module for Wildberries feedbacks - FIXED to match docs
"""
import time
import requests
import random
from typing import List, Dict, Optional
from utils import logger
from collections import deque  # not used

class WBAPI:
    """WB Feedbacks API https://feedbacks-api.wildberries.ru/api/v1 | Rate 3/sec burst 6"""
    
    BASE_URL = "https://feedbacks-api.wildberries.ru/api/v1"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": api_key,
            "Content-Type": "application/json"
        })
        self.last_time = 0.0
    
    def _rate_limit_sleep(self):
        now = time.time()
        sleep_duration = max(0, 0.34 - (now - self.last_time))
        if sleep_duration > 0:
            time.sleep(sleep_duration)
        self.last_time = time.time()
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Optional[Dict]:
        self._rate_limit_sleep()
        url = f"{self.BASE_URL}/{endpoint}"
        retries = 3
        for attempt in range(retries):
            try:
                if method.upper() == 'POST':
                    response = self.session.post(url, params=params, json=json_data)
                else:
                    response = self.session.get(url, params=params)
                
                if response.status_code == 204:
                    return True
                
                data = response.json()
                
                if not data.get('error', True):
                    return data.get('data')
                
                err_text = data.get('errorText', '')
                add_errors = data.get('additionalErrors', [])
                logger.error(f"WB [{endpoint}] HTTP{response.status_code}: {err_text} | {add_errors}")
                
                if response.status_code == 429:
                    backoff = 2 ** attempt + random.uniform(0, 1)
                    logger.warning(f"WB 429 - backoff {backoff:.1f}s")
                    time.sleep(backoff)
                    continue
                
                if attempt == retries - 1:
                    return None
                time.sleep(1.5 * (attempt + 1))
                
            except Exception as e:
                logger.error(f"WB [{endpoint}] exception: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None
        return None
    
    def get_unanswered_count(self) -> Dict:
        data = self._make_request("GET", "feedbacks/count-unanswered")
        count = data.get('countUnanswered', 0) if data else 0
        logger.info(f"WB unanswered: {count}")
        return data or {}
    
    def get_feedbacks(self, is_answered: bool = False, take: int = 500, skip: int = 0, date_from: Optional[int] = None, date_to: Optional[int] = None, nm_id: Optional[int] = None, order: str = "dateDesc") -> List[Dict]:
        params = {
            'isAnswered': is_answered,
            'take': min(5000, max(1, take)),
            'skip': min(199990, max(0, skip)),
            'order': order
        }
        if date_from:
            params['dateFrom'] = int(date_from)
        if date_to:
            params['dateTo'] = int(date_to)
        if nm_id:
            params['nmId'] = int(nm_id)
        
        data = self._make_request("GET", "feedbacks", params=params)
        feedbacks = data.get('feedbacks', []) if data else []
        if feedbacks:
            logger.info(f"WB batch {len(feedbacks)} feedbacks (unans: {data.get('countUnanswered', 0)})")
        return feedbacks
    
    def get_unanswered_feedbacks(self, limit: int = 1000) -> List[Dict]:
        all_fb = []
        skip = 0
        take = 500
        while len(all_fb) < limit:
            batch = self.get_feedbacks(False, take, skip)
            if not batch:
                break
            all_fb.extend(batch)
            if len(batch) < take:
                break
            skip += take
            time.sleep(0.2)  # extra caution
        logger.info(f"WB fetched {len(all_fb)} unanswered feedbacks")
        return all_fb[:limit]
    
    def send_answer(self, id_: str, text: str) -> bool:
        if not 2 <= len(text) <= 5000:
            logger.error(f"WB text len invalid: {len(text)}")
            return False
        data = {"id": id_, "text": text}
        result = self._make_request("POST", "feedbacks/answer", json_data=data)
        if result is True:
            logger.info(f"WB answer sent to feedback {id_}")
            return True
        logger.error(f"WB send failed {id_}: {result}")
        return False
