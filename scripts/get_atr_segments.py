import fsspec
import yaml

aeris = "https://observations.ipsl.fr/aeris/maestro/data/insitu/AIRCRAFT/ATR/YAML/"


def __main__():
    fs = fsspec.filesystem("http")
    files = fs.ls(aeris, detail=False)
    yamlfiles = [f for f in files if f[-4:] == "yaml"]

    for file in yamlfiles:
        with fsspec.open(file) as f:
            meta = yaml.safe_load(f)
            yaml.dump(
                meta,
                open(f"./flight_segment_files/{meta['safire_flight_id']}.yaml", "w"),
                sort_keys=False,
            )


if __name__ == "__main__":
    __main__()
