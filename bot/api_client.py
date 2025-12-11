# api_client.py
import requests
import time
import json
import os
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
        self._cache = {}
    
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
                "/api/docs",
                "/",
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
    
    def add_note(self, user_id: int, title: str, content: str, tags: Optional[str] = None) -> Optional[Dict]:
        """Создать новую заметку"""
        logger.info("add_note_request", user_id=user_id, title=title[:50])
        
        # Если API недоступен, используем локальное хранилище
        if not self.health_check():
            return self._add_note_local(user_id, title, content, tags)
        
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
            # Очищаем кэш для этого пользователя
            self._cache.pop(f"notes_{user_id}", None)
        else:
            # Если запрос не удался, используем локальное хранилище
            result = self._add_note_local(user_id, title, content, tags)
        
        return result
    
    def _add_note_local(self, user_id: int, title: str, content: str, tags: Optional[str] = None) -> Dict:
        """Локальное создание заметки (заглушка)"""
        note_id = int(time.time() * 1000)
        note = {
            "id": note_id,
            "user_id": user_id,
            "title": title,
            "content": content,
            "tags": tags,
            "created_at": time.time()
        }
        
        key = f"notes_{user_id}"
        if key not in self._cache:
            self._cache[key] = []
        
        self._cache[key].append(note)
        logger.info("add_note_local_success", 
                   user_id=user_id, 
                   note_id=note_id)
        
        return {"id": note_id, "title": title}
    
    def get_user_notes(self, user_id: int) -> List[Dict]:
        """Получить все заметки пользователя"""
        logger.info("get_user_notes_request", user_id=user_id)
        
        # Проверяем кэш
        cache_key = f"notes_{user_id}"
        if cache_key in self._cache:
            notes = self._cache[cache_key]
            logger.info("get_user_notes_from_cache", 
                       user_id=user_id,
                       note_count=len(notes))
            return notes
        
        # Если API доступен, пытаемся получить с сервера
        if self.health_check():
            result = self._make_request("GET", f"/api/notes/{user_id}")
            
            if isinstance(result, list):
                logger.info("get_user_notes_success", 
                           user_id=user_id,
                           note_count=len(result))
                # Сохраняем в кэш
                self._cache[cache_key] = result
                return result
        
        # Если не удалось, возвращаем пустой список
        logger.warning("get_user_notes_failed_or_empty", user_id=user_id)
        return []
    
    def search_notes(self, user_id: int, query: str) -> List[Dict]:
        """Поиск заметок"""
        logger.info("search_notes_request", 
                   user_id=user_id,
                   query=query[:50])
        
        # Получаем все заметки пользователя
        notes = self.get_user_notes(user_id)
        if not notes:
            return []
        
        # Простой поиск по заголовку и содержанию
        query_lower = query.lower()
        results = []
        for note in notes:
            title = note.get('title', '').lower()
            content = note.get('content', '').lower()
            tags = str(note.get('tags', '')).lower()
            
            if (query_lower in title or 
                query_lower in content or
                query_lower in tags):
                results.append(note)
        
        logger.info("search_notes_success",
                   user_id=user_id,
                   results_count=len(results))
        
        return results
    
    def get_note_graph(self, user_id: int) -> Dict:
        """Получить граф заметок"""
        logger.info("get_note_graph_request", user_id=user_id)
        
        # Если API доступен, пытаемся получить с сервера
        if self.health_check():
            result = self._make_request("GET", f"/api/notes/{user_id}/graph")
            
            if result and isinstance(result, dict):
                logger.info("get_note_graph_success",
                           user_id=user_id,
                           notes_count=len(result.get('notes', {})))
                return result
        
        # Создаем простой граф из локальных данных
        notes = self.get_user_notes(user_id)
        notes_dict = {}
        
        for note in notes:
            notes_dict[str(note['id'])] = {
                "id": note['id'],
                "title": note.get('title', 'Без названия'),
                "content": note.get('content', '')[:100],
                "links": []
            }
        
        graph_data = {
            "notes": notes_dict,
            "graph": {}
        }
        
        logger.info("get_note_graph_local",
                   user_id=user_id,
                   notes_count=len(notes))
        
        return graph_data
    
    def get_note_by_id(self, note_id: int, user_id: int) -> Optional[Dict]:
        """Получить заметку по ID"""
        logger.info("get_note_by_id_request", 
                   user_id=user_id,
                   note_id=note_id)
        
        # Если API доступен, пытаемся получить с сервера
        if self.health_check():
            result = self._make_request("GET", 
                                       f"/api/notes/{note_id}",
                                       params={"user_id": user_id})
            
            if result and isinstance(result, dict):
                logger.debug("get_note_by_id_success",
                            user_id=user_id,
                            note_id=note_id)
                return result
        
        # Ищем в локальных данных
        notes = self.get_user_notes(user_id)
        for note in notes:
            if note.get('id') == note_id:
                logger.debug("get_note_by_id_local_success",
                            user_id=user_id,
                            note_id=note_id)
                return note
        
        logger.warning("get_note_by_id_failed",
                     user_id=user_id,
                     note_id=note_id)
        return None
    
    def delete_note(self, note_id: int, user_id: int) -> bool:
        """Удалить заметку"""
        logger.info("delete_note_request",
                   user_id=user_id,
                   note_id=note_id)
        
        # Если API доступен, пытаемся удалить на сервере
        if self.health_check():
            result = self._make_request("DELETE",
                                       f"/api/notes/{note_id}",
                                       params={"user_id": user_id})
            
            if result is not None:
                logger.info("delete_note_success",
                           user_id=user_id,
                           note_id=note_id)
                # Очищаем кэш
                self._cache.pop(f"notes_{user_id}", None)
                return True
        
        # Удаляем локально
        cache_key = f"notes_{user_id}"
        if cache_key in self._cache:
            original_len = len(self._cache[cache_key])
            self._cache[cache_key] = [
                n for n in self._cache[cache_key] 
                if n.get('id') != note_id
            ]
            
            if len(self._cache[cache_key]) < original_len:
                logger.info("delete_note_local_success",
                           user_id=user_id,
                           note_id=note_id)
                return True
        
        logger.warning("delete_note_failed",
                     user_id=user_id,
                     note_id=note_id)
        return False