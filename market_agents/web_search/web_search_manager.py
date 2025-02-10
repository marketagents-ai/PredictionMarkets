import logging
import time
from typing import List

from googlesearch import search
from typing import List

from market_agents.web_search.web_search_config import WebSearchConfig


logger = logging.getLogger(__name__)
    
class SearchManager:
    def __init__(self, config: WebSearchConfig):
        self.config = config
        self.last_request_time = 0
        self.request_delay = 5
        self.max_retries = 3
        
        self.headers = self.config.headers.to_dict()
        
        self.search_params = {
            'stop': self.config.urls_per_query,
            'pause': 2.0,
            'user_agent': self.headers['User-Agent']
        }
        self.query_url_mapping = {}
        
    async def get_urls_for_query(self, query: str, num_results: int = 2) -> List[str]:
        """Get URLs from Google search with retry logic"""
        for attempt in range(self.max_retries):
            try:
                current_time = time.time()
                time_since_last_request = current_time - self.last_request_time
                if time_since_last_request < self.request_delay:
                    sleep_time = self.request_delay - time_since_last_request
                    logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                    time.sleep(sleep_time)
                
                urls = list(search(
                    term=query,
                    num_results=num_results,
                    lang="en",
                    sleep_interval=self.search_params.get('pause', 2),
                    timeout=self.config.request_timeout
                ))
                
                self.last_request_time = time.time()
                
                if urls:
                    logger.info(f"\n=== URLs Found ===")
                    logger.info(f"Query: {query}")
                    for i, url in enumerate(urls, 1):
                        logger.info(f"URL {i}: {url}")
                    logger.info("================")
                    
                    for url in urls:
                        self.query_url_mapping[url] = query
                    return urls
                    
            except Exception as e:
                logger.error(f"Search attempt {attempt + 1}/{self.max_retries} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    sleep_time = self.request_delay * (attempt + 1)
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                    
        logger.error(f"All search attempts failed for query: {query}")
        return []
