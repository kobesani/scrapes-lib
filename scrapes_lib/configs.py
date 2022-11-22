import dataclasses
import parsel
import requests
import yaml

from pathlib import Path
from requests import Response
from typing import Dict, List, Literal, Optional, Union


@dataclasses.dataclass
class SelectorConfig:
    attribute: str
    query: str
    query_type: Literal["xpath", "css"] = "xpath"
    # if parent is None, it inherits from main_selector
    parent: Optional[str] = None
    children: Optional[List[str]] = None
    _selector: Optional[Union[parsel.Selector, parsel.SelectorList]] = None
    text: Optional[Literal["normalize_space", "text"]] = None
    count: int = 1

    def selector(
        self, parent_selector: Union[parsel.Selector, parsel.SelectorList]
    ) -> Union[parsel.Selector, parsel.SelectorList]:
        if self._selector is None:
            self._selector = getattr(parent_selector, self.query_type)(self.query)
        return self._selector

    @property
    def is_leaf(self) -> bool:
        if self.children is None:
            return True

        if len(self.children) == 0:
            return True

        return False


@dataclasses.dataclass
class ScrapeConfig:
    base_url: str
    selectors: Dict[str, SelectorConfig]

    @property
    def parsel_selectors(
        self,
    ) -> List[Optional[Union[parsel.Selector, parsel.SelectorList]]]:
        return [x.selector for x in self.selectors.values()]

    @property
    def parsel_selectors_defined(self) -> bool:
        return all(self.parsel_selectors)


def set_selectors(response: Response, selector_configs: List[SelectorConfig]):
    selectors_dict: Dict[str, Optional[Union[parsel.Selector, parsel.SelectorList]]] = {
        "main": parsel.Selector(response.text)
    }

    for selector_config in selector_configs:
        selectors_dict.setdefault(selector_config.attribute, None)

    while not all(selectors_dict.values()):
        for selector_config in selector_configs:
            if not selectors_dict[selector_config.parent or "main"]:
                continue
            selectors_dict[selector_config.attribute] = selector_config.selector(
                selectors_dict[selector_config.parent or "main"]
            )

    return selectors_dict


def load_selector_config(config_path: Path) -> List[SelectorConfig]:
    with open(config_path) as config_file:
        parsed_yaml = yaml.safe_load(config_file)

    return [SelectorConfig(**selector) for selector in parsed_yaml["selectors"]]


def test_selector_setting(
    url: str = "https://vlr.gg/matches/results",
    config_path: Path = Path(__file__).parent / "vlr-gg-results.yaml",
):
    selector_configs = load_selector_config(config_path)
    response = requests.get(url)
    return selector_configs, set_selectors(response, selector_configs)
