import enum
import json

from typing import Any, Tuple, Dict


class UrlParser:
    
    @staticmethod
    def unquote(s: str) -> str:
        """
        "Nguy%C3%AAn+H%C3%A0" -> "Nguyên Hà"
        """
        if not s:
            return ""
        
        res_bytes = bytearray()
        i = 0
        n = len(s)
        
        while i < n:
            char = s[i]
            if char == '%':
                if i + 2 < n:
                    try:
                        hex_val = int(s[i+1:i+3], 16)
                        res_bytes.append(hex_val)
                        i += 3
                        continue
                    except ValueError:
                        res_bytes.append(ord('%'))
                        i += 1
                else:
                    res_bytes.append(ord('%'))
                    i += 1
            elif char == '+':
                res_bytes.append(ord(' '))
                i += 1
            else:
                res_bytes.append(ord(char))
                i += 1
        
        return res_bytes.decode('utf-8', 'ignore')

    @staticmethod
    def parse_qs(query_string: str) -> Dict[str, str]:
        """
        "id=1&name=A" -> {'id': '1', 'name': 'A'}
        """
        query_params = {}
        if not query_string:
            return query_params
            
        pairs = query_string.split('&')
        for pair in pairs:
            if not pair:
                continue
            
            if '=' in pair:
                key, value = pair.split('=', 1)
                decoded_key = UrlParser.unquote(key)
                decoded_val = UrlParser.unquote(value)
                query_params[decoded_key] = decoded_val
            else:
                decoded_key = UrlParser.unquote(pair)
                query_params[decoded_key] = ''
                
        return query_params

    @staticmethod
    def parse_url(raw_path: str) -> Tuple[str, Dict[str, str]]:
        if '?' in raw_path:
            path_part, query_part = raw_path.split('?', 1)
            if '#' in query_part:
                query_part = query_part.split('#', 1)[0]
            return path_part, UrlParser.parse_qs(query_part)
        else:
            if '#' in raw_path:
                path_part = raw_path.split('#', 1)[0]
                return path_part, {}
            return raw_path, {}
        

class RequestBodyParser:

    class Type(enum.StrEnum):
        TEXT = 'text/plain'
        FORM = 'application/x-www-form-urlencoded'
        JSON = 'application/json'
        XML = 'application/xml'

    @staticmethod
    def parse(content_type: str, content: bytes) -> Dict[str, Any]:
        _t = RequestBodyParser.Type
        if content_type.startswith((_t.FORM, _t.TEXT)):
            return RequestBodyParser.parse_form(content.decode('utf-8', 'ignore'))
        elif content_type.startswith(_t.JSON):
            return RequestBodyParser.parse_json(content)
        elif content_type.startswith(_t.XML):
            return RequestBodyParser.parse_xml(content)
        else:
            raise TypeError(f'Unsupported Content-Type: {content_type}')
        
    @staticmethod
    def parse_form(content: str) -> Dict[str, Any]:
        return UrlParser.parse_qs(content)

    @staticmethod
    def parse_json(content: bytes) -> Dict[str, Any]:
        try:
            return json.loads(content.decode('utf-8'))
        except Exception:
            raise ValueError('Invalid JSON body')

    @staticmethod
    def parse_xml(content: bytes) -> Dict[str, Any]:
        raise NotImplementedError('XML parsing not implemented')
    
