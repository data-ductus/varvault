from typing import Dict, Any, List, Tuple


class Function:
    def __init__(self, fn, *fn_args: Any, **fn_kwargs: Any):
        assert callable(fn), "fn object is not callable (e.g. a function)"
        self.fn = fn
        self.fn_path = f"{self.fn.__module__}.{self.fn.__name__}"
        self.fn_args: Tuple[Any, ...] = fn_args
        self.fn_kwargs: Dict[str, Any] = fn_kwargs

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"fn={self.fn.__name__}; fn_args={self.fn_args}, fn_kwargs={self.fn_kwargs}"


class ResultStruct:
    def __init__(self, function: Function, result):
        self.function = function

        self.fn_name = function.fn.__name__
        self.result = result

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"(function={self.fn_name}; result={self.result})"


class ResultList(list):
    def __init__(self, results: List[ResultStruct] = None):
        if results:
            super(ResultList, self).__init__(results)
        else:
            super(ResultList, self).__init__()

    def get(self, fn_name: str) -> List[ResultStruct]:
        results = list()
        for r in self:
            r: ResultStruct
            if r.fn_name == fn_name:
                results.append(r)
        return results

    def asdict(self):
        d: Dict[str, List[ResultStruct]] = dict()
        for r in self:
            r: ResultStruct
            if r.fn_name not in d:
                d[r.fn_name] = list()
            d[r.fn_name].append(r.result)

        return d

