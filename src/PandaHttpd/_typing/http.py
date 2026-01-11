from .base import SupportsStr
from typing import Dict, Union, Iterable


HeadersType = Dict[str, Union[SupportsStr, str, Iterable[SupportsStr], Iterable[str]]]
HTTPMethod = str
HTTPPath = str
HTTPStatusLine = str
