import parsel
import requests
import uplink
import yaml

from pathlib import Path
from typing import Dict, Optional, Union

from scrapes_lib.configs import SelectorConfig
from scrapes_lib.utils import TextUtils


class Scraper(uplink.Consumer):
    def __init__(self, config_path: Path, *args, **kwargs):
        with open(config_path) as config_file:
            parsed_yaml = yaml.safe_load(config_file)

        self.base_url = parsed_yaml["base_url"]
        self.selector_configs = [
            SelectorConfig(**selector) for selector in parsed_yaml["selectors"]
        ]

        super().__init__(base_url=self.base_url, *args, **kwargs)

    def get_selectors(self, response: requests.Response):
        selectors_dict: Dict[
            str, Optional[Union[parsel.Selector, parsel.SelectorList]]
        ] = {"main": parsel.Selector(response.text)}

        for selector_config in self.selector_configs:
            selectors_dict.setdefault(selector_config.attribute, None)

        selectors_retrieved: Dict[str, Optional[bool]] = {"main": True} | {
            x.attribute: False for x in self.selector_configs
        }

        while not all(selectors_retrieved.values()):
            for selector_config in self.selector_configs:
                # parent is None => parent is main selector
                if not selectors_retrieved[selector_config.parent or "main"]:
                    continue

                selectors_dict[selector_config.attribute] = selector_config.selector(
                    selectors_dict[selector_config.parent or "main"]
                )
                selectors_retrieved[selector_config.attribute] = True

        return selectors_dict

    def scrape_endpoint(self, endpoint: str, *args, **kwargs):
        response = getattr(self, endpoint)(*args, **kwargs)
        selectors_dict = self.get_selectors(response)

        return {
            selector_config.attribute: TextUtils.apply(
                selector_config.text,
                selectors_dict[selector_config.attribute],
            )
            for selector_config in self.selector_configs
            if selector_config.is_leaf
        }
