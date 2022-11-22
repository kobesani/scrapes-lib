import parsel

from typing import List, Optional, Union


class TextUtils:
    methods = (
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

    @classmethod
    def apply(
        cls,
        method: Optional[str],
        selector: Union[parsel.Selector, parsel.SelectorList],
    ) -> List[str]:
        match method:
            case method if method in cls.methods:
                return getattr(cls, method)(selector)
            case method if method is None:
                return selector.getall()
            case other:
                raise ValueError(
                    f"{method} not a valid text method\nSee: {cls.methods}"
                )
