from __future__ import annotations

import os
from typing import TYPE_CHECKING, MutableMapping

from socket import socket as Socket
from typing import (
    Any, 
    Callable, 
    Optional,
    Union, 
    Type, 
    TypeVar, 
    Protocol, 
    runtime_checkable
)

if TYPE_CHECKING:
    from ..http import Response
    from ..app import PandaHttpd
    from ..utils import MappingStr


HandleFunc = Callable[[Socket, Optional[Socket]], None]
UserFunc = Callable[..., Any]

@runtime_checkable
class HasPrefix(Protocol):
    
    @property
    def prefix(self) -> str | os.PathLike: ...
    
    
class GenericHandler(Protocol):
    def __call__(self, *args: Any, **kwds: Any) -> 'Response': ...
    
        
class HeaderHandler(Protocol):
    def __call__(self, dict_headers: MappingStr | None, *args: Any, **kwds: Any) -> Response: ...
    
AnyHandler = Union[GenericHandler, HeaderHandler]
