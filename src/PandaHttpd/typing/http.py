from .base import SupportsStr
from typing import Union, Iterable

HeadersType = dict[str, Union[SupportsStr, str, Iterable[SupportsStr], Iterable[str]]]
HTTPMethod = str
HTTPPath = str
HTTPStatusLine = str
