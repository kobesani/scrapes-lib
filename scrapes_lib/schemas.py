import dataclasses
import pendulum


@dataclasses.dataclass
class ResultData:
    # base_url: str
    event: str
    link: str
    map_stats: bool
    player_stats: bool
    stakes: str
    start_timestamp: pendulum.datetime
    status: str
