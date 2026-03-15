from typing import Any, Callable, Dict, List


ToolFn = Callable[[Dict[str, Any]], Any]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolFn] = {}

    def register(self, name: str, fn: ToolFn) -> None:
        self._tools[name] = fn

    def list_tools(self) -> List[str]:
        return sorted(self._tools.keys())

    def run(self, name: str, inp: Dict[str, Any]) -> Any:
        if name not in self._tools:
            return {"ok": False, "error": f"unknown tool: {name}"}
        try:
            return self._tools[name](inp or {})
        except Exception as e:
            return {"ok": False, "error": str(e)}
