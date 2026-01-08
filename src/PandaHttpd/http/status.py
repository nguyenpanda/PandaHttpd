from enum import IntEnum, Enum


class HttpStatus(IntEnum):
	OK = (200, 'OK')
	CREATED = (201, 'Created')
	ACCEPTED = (202, 'Accepted')
	NON_AUTHORITATIVE_INFORMATION = (203, 'Non-Authoritative Information')
	NO_CONTENT = (204, 'No Content')
	RESET_CONTENT = (205, 'Reset Content')
	PARTIAL_CONTENT = (206, 'Partial Content')
	
	MULTIPLE_CHOICES = (300, 'Multiple Choices')
	MOVED_PERMANENTLY = (301, 'Moved Permanently')
	FOUND = (302, 'Found')
	SEE_OTHER = (303, 'See Other')
	NOT_MODIFIED = (304, 'Not Modified')
	USE_PROXY = (305, 'Use Proxy')
	SWITCH_PROXY = (306, 'Switch Proxy')
	TEMPORARY_REDIRECT = (307, 'Temporary Redirect')
	PERMANENT_REDIRECT = (308, 'Permanent Redirect')
	
	BAD_REQUEST = (400, 'Bad Request')
	UNAUTHORIZED = (401, 'Unauthorized')
	PAYMENT_REQUIRED = (402, 'Payment Required')
	FORBIDDEN = (403, 'Forbidden')
	NOT_FOUND = (404, 'Not Found')
	METHOD_NOT_ALLOWED = (405, 'Method Not Allowed')
	NOT_ACCEPTABLE = (406, 'Not Acceptable')
	PROXY_AUTHENTICATION_REQUIRED = (407, 'Proxy Authentication Required')
	REQUEST_TIMEOUT = (408, 'Request Timeout')
	CONFLICT = (409, 'Conflict')
	GONE = (410, 'Gone')
	LENGTH_REQUIRED = (411, 'Length Required')
	PRECONDITION_FAILED = (412, 'Precondition Failed')
	PAYLOAD_TOO_LARGE = (413, 'Payload Too Large')
	URI_TOO_LONG = (414, 'URI Too Long')
	UNSUPPORTED_MEDIA_TYPE = (415, 'Unsupported Media Type')
	RANGE_NOT_SATISFIABLE = (416, 'Range Not Satisfiable')
	EXPECTATION_FAILED = (417, 'Expectation Failed')
	UPGRADE_REQUIRED = (426, 'Upgrade Required')
	PRECONDITION_REQUIRED = (428, 'Precondition Required')
	TOO_MANY_REQUESTS = (429, 'Too Many Requests')
	REQUEST_HEADER_FIELDS_TOO_LARGE = (431, 'Request Header Fields Too Large')
	UNAVAILABLE_FOR_LEGAL_REASONS = (451, 'Unavailable For Legal Reasons')
	
	INTERNAL_SERVER_ERROR = (500, 'Internal Server Error')
	NOT_IMPLEMENTED = (501, 'Not Implemented')
	BAD_GATEWAY = (502, 'Bad Gateway')
	SERVICE_UNAVAILABLE = (503, 'Service Unavailable')
	GATEWAY_TIMEOUT = (504, 'Gateway Timeout')
	HTTP_VERSION_NOT_SUPPORTED = (505, 'HTTP Version Not Supported')
	NETWORK_AUTHENTICATION_REQUIRED = (511, 'Network Authentication Required')

	def __new__(cls, code, phrase, description=''):
		obj = int.__new__(cls, code)
		obj._value_ = code
		obj.phrase = phrase
		obj.description = description
		return obj

	@property
	def code(self):
		return self.value

	@code.setter
	def code(self, value):
		self._value_ = value

	@property
	def phrase(self):
		return self._phrase

	@phrase.setter
	def phrase(self, value):
		self._phrase = value

	@property
	def description(self):
		return self._description

	@description.setter
	def description(self, value):
		self._description = value

	@property
	def is_success(self):
		return 200 <= self.value < 300

	@property
	def is_redirect(self):
		return 300 <= self.value < 400

	@property
	def is_client_error(self):
		return 400 <= self.value < 500

	@property
	def is_server_error(self):
		return 500 <= self.value < 600

	@property
	def is_error(self):
		return self.is_client_error or self.is_server_error

	@property
	def category(self):
		if self.is_success:
			return 'Success'
		elif self.is_redirect:
			return 'Redirection'
		elif self.is_client_error:
			return 'Client Error'
		elif self.is_server_error:
			return 'Server Error'
		else:
			return 'Informational'

	def __str__(self):
		return f'{self.__class__.__name__}({self.value})'


if __name__ == '__main__':
	for status in HttpStatus:
		print(f'{status.value} {status.phrase} - {status.description}')
  
	print(HttpStatus.NOT_FOUND.is_success)
	