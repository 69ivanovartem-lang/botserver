# api_client.py
import requests
from typing import Optional, List, Dict, Any
from config import logger, API_URL

class APIClient:
    def __init__(self, base_url: str = API_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Zettelkasten-Bot/1.0'
        })
        logger.info("api_client_initialized", base_url=base_url)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Универсальный метод для выполнения запросов"""
        url = f"{self.base_url}{endpoint}"
        
        log_context = {
            "method": method,
            "url": url,
            "endpoint": endpoint
        }
        
        try:
            logger.debug("api_request_start", **log_context)
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            logger.debug("api_request_success", 
                        **log_context,
                        status_code=response.status_code)
            
            if response.status_code != 204:  # No Content
                return response.json()
            return {}
            
        except requests.exceptions.HTTPError as e:
            logger.error("api_request_http_error",
                        **log_context,
                        status_code=e.response.status_code if e.response else None,
                        error=str(e))
        except requests.exceptions.ConnectionError as e:
            logger.error("api_connection_error",
                        **log_context,
                        error=str(e))
        except requests.exceptions.Timeout as e:
            logger.error("api_timeout_error",
                        **log_context,
                        error=str(e))
        except requests.exceptions.RequestException as e:
            logger.error("api_request_exception",
                        **log_context,
                        error=str(e))
        except ValueError as e:  # JSON decode error
            logger.error("api_json_decode_error",
                        **log_context,
                        error=str(e))
        except Exception as e:
            logger.error("api_unexpected_error",
                        **log_context,
                        error=str(e),
                        exc_info=True)
        
        return None
    
    def health_check(self) -> bool:
        """Проверка доступности API"""
        try:
            # Пробуем несколько эндпоинтов
            endpoints_to_check = [
                "/health",
                "/api/health",
                "/api/docs",  # если используется FastAPI
                "/",  # корневой эндпоинт
            ]
            
            for endpoint in endpoints_to_check:
                try:
                    response = self.session.get(
                        f"{self.base_url}{endpoint}", 
                        timeout=3
                    )
                    if response.status_code < 500:
                        logger.debug("api_health_check_success", 
                                    endpoint=endpoint,
                                    status_code=response.status_code)
                        return True
                except:
                    continue
            
            logger.warning("api_health_check_failed", api_url=self.base_url)
            return False
            
        except Exception as e:
            logger.warning("api_health_check_exception", 
                         error=str(e),
                         api_url=self.base_url)
            return False
    
    # ... остальные методы остаются без изменений ...