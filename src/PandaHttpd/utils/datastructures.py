from typing import (
    Any, 
    Mapping, 
    MutableMapping, 
    Iterator, 
    Optional
)


MappingStr = MutableMapping[str, str]


class CaseInsensitiveDict(MappingStr):
    """
    A case-insensitive dictionary optimized for HTTP headers.
    
    Stores all keys in lowercase but preserves original casing if needed 
    (though this specific implementation normalizes to lowercase for storage).
    
    Example:
        headers = CaseInsensitiveDict({"Content-Type": "application/json"})
        headers["content-type"]  # Returns "application/json"
    """

    def __init__(self, data: Optional[MappingStr] = None, **kwargs: str) -> None:
        self._store: dict[str, str] = {}
        self.update(data or {}, **kwargs)

    def __setitem__(self, key: str, value: str) -> None:
        self._store[key.lower()] = value

    def __getitem__(self, key: str) -> str:
        return self._store[key.lower()]

    def __delitem__(self, key: str) -> None:
        del self._store[key.lower()]

    def __iter__(self) -> Iterator[str]:
        return iter(self._store)

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: object) -> bool:
        if isinstance(key, str):
            return key.lower() in self._store
        return False

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key.lower(), default)

    def pop(self, key: str, default: Any = None) -> Any:
        return self._store.pop(key.lower(), default)

    def __repr__(self) -> str:
        return f"CaseInsensitiveDict({self._store!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Mapping):
            other_items = {k.lower(): v for k, v in other.items()}
            return self._store == other_items
        return NotImplemented
    
    def to_dict(self) -> dict[str, str]:
        """Returns a standard dictionary representation of the headers."""
        return dict(self._store)


class CookieDict(MappingStr):
    """
    A strictly typed dictionary for HTTP Cookies.
    Enforces that both keys and values are strings to prevent serialization errors.
    """

    def __init__(self, data: Optional[MappingStr] = None, **kwargs: str) -> None:
        self._store: dict[str, str] = {}
        self.update(data or {}, **kwargs)

    def __setitem__(self, key: str, value: str) -> None:
        if not isinstance(key, str) or not isinstance(value, str):
            raise TypeError(f"Cookie keys and values must be strings. Got key={type(key)}, value={type(value)}")
        self._store[key] = value

    def __getitem__(self, key: str) -> str:
        return self._store[key]

    def __delitem__(self, key: str) -> None:
        del self._store[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._store)

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: object) -> bool:
        return key in self._store

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)
    
    def pop(self, key: str, default: Any = None) -> Any:
        return self._store.pop(key, default)

    def __repr__(self) -> str:
        return f"CookieDict({self._store!r})"
    
    def to_dict(self) -> dict[str, str]:
        """Returns a standard dictionary representation of the cookies."""
        return dict(self._store)
    