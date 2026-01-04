from .respone_code import RESPONSE_CODES
from ..typing import HeadersType

from typing import Optional

class HttpHeader:

	def __init__(self, headers: HeadersType = {}) -> None:
		self.headers: HeadersType = headers


	@staticmethod
	def parse(raw_headers: str) -> 'HttpHeader':
		headers: HeadersType = {}
		lines = raw_headers.split('\r\n')
		for line in lines:
			if ':' in line:
				key, value = line.split(':', 1)
				headers[key.strip().lower()] = value.strip()
		return HttpHeader(headers)

	@staticmethod
	def status_line(code: int, http_version: str = '1.1') -> str:
		reason = RESPONSE_CODES.get(code, 'Unknown Status')
		return f'HTTP/{http_version} {code} {reason}'

	@staticmethod
	def build(status_code: int, headers: Optional[HeadersType] = None) -> bytes:
		http_header = HttpHeader.status_line(status_code) + '\r\n'
		if headers:
			for key, value in headers.items():
				if isinstance(value, (list, tuple)):
					for v in value:
						http_header += f'{key}: {str(v)}\r\n'
				else:
					http_header += f'{key}: {str(value)}\r\n'
		http_header += '\r\n'
		return http_header.encode('utf-8')
