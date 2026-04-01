import yaml
import fsspec
import frontmatter
from collections import defaultdict
from utils import segment_hash

def normalize_atr_segment(segment, flight_id):
    return {
        "segment_id": f"{flight_id}_{segment_hash(slice(segment["start"], segment["end"]))}",
        "name": segment["name"],
        "start": segment["start"],
        "end": segment["end"],
        "kinds": segment["kind"],
        "remarks": segment.get("note") or [],
    }

def add_halo_nickname(flight_id):
    url = f"https://raw.githubusercontent.com/orcestra-campaign/book/refs/heads/main/orcestra_book/reports/{flight_id}.md"
    try:
        with fsspec.open(url, "r") as f:
            metadata = frontmatter.load(f)
            ret = metadata["nickname"]
    except FileNotFoundError:
        ret = None
    return ret

def normalize_segmentation(meta):
    if meta["mission"]=="MAESTRO":
        meta["platform"] = "ATR"
        #meta["atr_flight_id"] = meta["flight_id"]
        meta["flight_id"] = meta["orcestra_flight_id"]
        del meta["orcestra_flight_id"]
        meta["remarks"] = meta.get("remarks") or []
        meta["events"] = meta.get("events") or []
        meta["segments"] = [normalize_atr_segment(seg, meta["flight_id"]) for seg in meta["segments"]]
    elif meta["platform"]=="HALO":
        meta["date"] = str(meta["takeoff"].date())
        meta["flight_report"] = f"https://orcestra-campaign.org/reports/{meta["flight_id"]}.html"
        meta["contacts"] = [{"name": "Bjorn Stevens", "email": "bjorn.stevens@mpimet.mpg.de"},
                            {"name": "Silke Groß", "email": "silke.gross@dlr.de"},
                            {"name": "Julia Windmiller", "email": "julia.windmiller@mpimet.mpg.de"},
                            ]
        meta["remarks"] = meta.get("remarks") or []
        meta["name"] = add_halo_nickname(meta["flight_id"])

    keys = ["mission", "platform", "flight_id", "name",
            "date", "takeoff", "landing",
            "flight_report", "contacts", "remarks",
            "events", "segments",
            ]
    ordered_dict = {key: meta[key] for key in keys}

    return ordered_dict

def __main__():
    import argparse
    parser = argparse.ArgumentParser(description="Merge flight segment files")
    parser.add_argument("-i", "--input", type=str, nargs="+", help="input files")
    parser.add_argument("-o", "--output", type=str, help="output file")
    args = parser.parse_args()

    all_flights = defaultdict(dict)

    for file in args.input:
        with open(file) as f:
            meta = normalize_segmentation(yaml.safe_load(f))
            flight_id = meta["flight_id"]
            platform = meta["platform"]
            all_flights[platform][flight_id] = meta
    
    all_flights = {**all_flights}

    with open(args.output, "w") as f:
        yaml.dump(all_flights, f, sort_keys=False)
            

if __name__ == "__main__":
    __main__()