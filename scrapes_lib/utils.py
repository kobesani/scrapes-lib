import parsel

from typing import List, Optional, Union


class TextUtils:
    methods = (
        "selector_directly",
        "normalize_space",
        "raw_text",
    )

    @staticmethod
    def normalize_space(
        selector: Union[parsel.Selector, parsel.SelectorList]
    ) -> List[str]:
        return selector.xpath("normalize-space(./text())").getall()

    @staticmethod
    def raw_text(selector: Union[parsel.Selector, parsel.SelectorList]) -> List[str]:
        return selector.xpath("./text()").getall()

    @staticmethod
    def selector_directly(selector: Union[parsel.Selector, parsel.SelectorList]):
        return selector.getall()

    @classmethod
    def apply(
        cls,
        method: Optional[str],
        selector: Union[parsel.Selector, parsel.SelectorList],
    ) -> List[str]:
        if method is None:
            return selector.getall()

        if method not in cls.methods:
            raise ValueError(f"{method} not a valid text method\nSee: {cls.methods}")

        return getattr(cls, method)(selector)