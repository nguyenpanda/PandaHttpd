from __future__ import annotations
from typing import TYPE_CHECKING

from socket import socket as Socket
from typing import Callable, Optional

if TYPE_CHECKING:
    from ..http import Response

HandleFunc = Callable[[Socket, Optional[Socket]], None]
ResponseFunc = Callable[..., 'Response']
