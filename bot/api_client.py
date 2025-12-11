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
    
    def add_note(self, user_id: int, title: str, content: str, tags: Optional[str] = None) -> Optional[Dict]:
        """Создать новую заметку"""
        logger.info("add_note_request", user_id=user_id, title=title[:50])
        
        data = {
            "user_id": user_id,
            "title": title,
            "content": content,
            "tags": tags
        }
        
        result = self._make_request("POST", "/api/notes", json=data)
        
        if result:
            logger.info("add_note_success", 
                       user_id=user_id, 
                       note_id=result.get('id'))
        else:
            logger.warning("add_note_failed", user_id=user_id)
        
        return result
    
    def get_user_notes(self, user_id: int) -> List[Dict]:
        """Получить все заметки пользователя"""
        logger.info("get_user_notes_request", user_id=user_id)
        
        result = self._make_request("GET", f"/api/notes/{user_id}")
        
        if isinstance(result, list):
            logger.info("get_user_notes_success", 
                       user_id=user_id,
                       note_count=len(result))
            return result
        else:
            logger.warning("get_user_notes_failed", user_id=user_id)
            return []
    
    def search_notes(self, user_id: int, query: str) -> List[Dict]:
        """Поиск заметок"""
        logger.info("search_notes_request", 
                   user_id=user_id,
                   query=query[:50])
        
        result = self._make_request("GET", 
                                   f"/api/notes/{user_id}/search",
                                   params={"q": query})
        
        if isinstance(result, list):
            logger.info("search_notes_success",
                       user_id=user_id,
                       results_count=len(result))
            return result
        else:
            logger.warning("search_notes_failed", user_id=user_id)
            return []
    
    def get_note_graph(self, user_id: int) -> Dict:
        """Получить граф заметок"""
        logger.info("get_note_graph_request", user_id=user_id)
        
        result = self._make_request("GET", f"/api/notes/{user_id}/graph")
        
        if result:
            logger.info("get_note_graph_success",
                       user_id=user_id,
                       notes_count=len(result.get('notes', {})))
            return result
        else:
            logger.warning("get_note_graph_failed", user_id=user_id)
            return {"notes": {}, "graph": {}}
    
    def add_link(self, from_note_id: int, to_note_id: int, user_id: int) -> bool:
        """Добавить связь между заметками"""
        logger.info("add_link_request",
                   user_id=user_id,
                   from_note_id=from_note_id,
                   to_note_id=to_note_id)
        
        data = {
            "from_note_id": from_note_id,
            "to_note_id": to_note_id,
            "user_id": user_id
        }
        
        result = self._make_request("POST", "/api/links", json=data)
        
        success = result is not None
        if success:
            logger.info("add_link_success",
                       user_id=user_id,
                       from_note_id=from_note_id,
                       to_note_id=to_note_id)
        else:
            logger.warning("add_link_failed",
                         user_id=user_id,
                         from_note_id=from_note_id,
                         to_note_id=to_note_id)
        
        return success
    
    def delete_note(self, note_id: int, user_id: int) -> bool:
        """Удалить заметку"""
        logger.info("delete_note_request",
                   user_id=user_id,
                   note_id=note_id)
        
        result = self._make_request("DELETE",
                                   f"/api/notes/{note_id}",
                                   params={"user_id": user_id})
        
        success = result is not None
        if success:
            logger.info("delete_note_success",
                       user_id=user_id,
                       note_id=note_id)
        else:
            logger.warning("delete_note_failed",
                         user_id=user_id,
                         note_id=note_id)
        
        return success
    
    def health_check(self) -> bool:
        """Проверка доступности API"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            is_healthy = response.status_code == 200
            logger.debug("api_health_check", 
                        status=is_healthy,
                        status_code=response.status_code)
            return is_healthy
        except Exception as e:
            logger.warning("api_health_check_failed", error=str(e))
            return False