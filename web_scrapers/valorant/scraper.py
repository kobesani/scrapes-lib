import dataclasses
import gzip
import json
import parsel
import pendulum
import requests
import uplink

from datetime import date, datetime
from functools import partial
from google.cloud import storage
from io import BytesIO
from typing import Any, List

from scrapes_lib import Scraper
from scrapes_lib.schemas import ResultData

def timestamp_in_range(
    query: ResultData, start: pendulum.datetime, end: pendulum.datetime
) -> bool:
    return (query.start_timestamp >= start) and (query.start_timestamp < end)


def json_serial(obj: Any) -> str:
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (date, datetime)):
        return obj.isoformat()

    raise TypeError("Type %s not serializable" % type(obj))


class Valorant(Scraper):
    @uplink.get("/matches/results")
    def get_results_page(
        self, page: uplink.Query("page", type=int)
    ) -> requests.Response:
        pass

    @uplink.get("/{match_id}/{match_stub}")
    def get_match(
        self,
        match_id: uplink.Path("match_id", type=int),
        match_stub: uplink.Path("match_stub", type=str),
    ) -> requests.Response:
        pass



class OldValorantResults(uplink.Consumer):
    def __init__(self, *args, **kwargs):
        super().__init__(base_url="https://vlr.gg", *args, **kwargs)

    @uplink.get("/matches/results")
    def get_results_page(
        self, page: uplink.Query("page", type=int)
    ) -> requests.Response:
        pass

    def parse_results_page(self, page: int) -> List[ResultData]:
        response = self.get_results_page(page=page)
        main_selector = parsel.Selector(response.text)
        cards = main_selector.xpath("//div[@class='wf-card']")
        dates = (
            main_selector.xpath("//div[@class='wf-label mod-large']")
            .xpath("normalize-space(./text())")
            .getall()
        )

        matches = []

        for date, card in zip(dates, cards):
            for match_selector in card.xpath(
                "./a[contains(@class, 'wf-module-item match-item')]"
            ):
                data = {}
                data["link"] = match_selector.xpath("@href").get()
                data["status"] = (
                    match_selector.xpath(
                        "./div[@class='match-item-eta']/div[contains(@class, 'ml')]/div[@class='ml-status']"
                    )
                    .xpath("normalize-space(./text())")
                    .get()
                )
                map_stats = (
                    match_selector.xpath(
                        "./div[@class='match-item-vod']/div[@class='wf-tag mod-big'][1]"
                    )
                    .xpath("normalize-space(./text())")
                    .get()
                )
                data["map_stats"] = True if map_stats is not None else False

                player_stats = (
                    match_selector.xpath(
                        "./div[@class='match-item-vod']/div[@class='wf-tag mod-big'][2]"
                    )
                    .xpath("normalize-space(./text())")
                    .get()
                )
                data["player_stats"] = True if map_stats is not None else False

                data["event"] = (
                    match_selector.xpath("./div[contains(@class, 'match-item-event')]")
                    .xpath("normalize-space(./text()[last()])")
                    .get()
                )
                data["stakes"] = (
                    match_selector.xpath(
                        "./div[contains(@class, 'match-item-event')]/div[@class='match-item-event-series text-of']"
                    )
                    .xpath("normalize-space(./text()[last()])")
                    .get()
                )
                start_timestamp = (
                    match_selector.xpath("./div[@class='match-item-time']")
                    .xpath("normalize-space(./text())")
                    .get()
                )
                data["start_timestamp"] = pendulum.from_format(
                    f"{date} {start_timestamp}",
                    "ddd, MMMM DD, YYYY hh:mm A",
                    tz=pendulum.now().tz,
                ).astimezone(pendulum.timezone("UTC"))
                matches.append(ResultData(**data))

        return matches

    def filter_matches_in_range(
        self,
        matches: List[ResultData],
        start: pendulum.datetime,
        end: pendulum.datetime,
    ) -> List[ResultData]:
        return filter(partial(timestamp_in_range, start=start, end=end), matches)

    def get_matches_in_timeframe(self, timestamp_isoformat: str) -> List[ResultData]:
        end_interval = pendulum.parse(timestamp_isoformat).in_tz(
            pendulum.timezone("UTC")
        )
        start_interval = end_interval.subtract(days=1)
        interval_started = False
        interval_completed = False
        next_page = 1
        matches_in_range = []

        while not (interval_completed):
            print(f"Starting parsing page={next_page}")
            # matches = self.get_matches_from_results_page(next_page)
            matches = self.parse_results_page(next_page)

            matches_in_range += self.filter_matches_in_range(
                matches, start_interval, end_interval
            )

            if not (interval_started):
                interval_started = matches[0].start_timestamp > end_interval

            interval_completed = interval_started and (
                matches[-1].start_timestamp < start_interval
            )

            next_page += 1

        # return "\n".join([x.asjson() for x in matches_in_range])
        return matches_in_range

    def upload_to_gcs(
        self, data: List[ResultData], bucket_name: str, destination_blob_name: str
    ):
        data_json = "\n".join(
            [json.dumps(dataclasses.asdict(x), default=json_serial) for x in data]
        )
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(bucket)
        blob = bucket.blob(blob_name=destination_blob_name)
        mime_type = "application/x-gzip"
        bytes_json = bytes(data_json, encoding="utf-8")
        out_json_gzip = BytesIO()
        with gzip.GzipFile(fileobj=out_json_gzip, mode="w") as f:
            f.write(bytes_json)
        gzipped_json = out_json_gzip.getvalue()
        blob.upload_from_string(data=gzipped_json, content_type=mime_type)

        return data_json
