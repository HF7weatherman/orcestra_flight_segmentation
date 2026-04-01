# some untility functions for defining segments

__all__ = [
    "get_sondes_l2",
    "get_overpass_point",
    "plot_overpass_point",
    "get_overpass_track",
    "get_ec_track",
    "ec_event",
    "pace_event",
    "meteor_event",
    "target_event",
    "to_dt",
    "get_takeoff_landing",
    "segment_hash",
    "event_hash",
    "parse_segment",
    "to_yaml",
    "ransac_fit_circle",
]

def get_sondes_l2(flight_id):
    import fsspec
    import json
    import pandas as pd
    root = "ipfs://QmZt6716gkTQoREiNdvzWdVpAJ8h2eq3zbR16vWuLYKXCt"
    day_folder = root + "/Level_2/" + flight_id
    protocol = day_folder.split(":")[0]
    fs = fsspec.filesystem(protocol)
    filenames = [fn.split("/")[-1] + "/.zattrs" for fn in fs.ls(day_folder, detail=False)]
    m = fsspec.get_mapper(day_folder)
    zattrs = [json.loads(v) for v in m.getitems(filenames).values()]
    df = pd.DataFrame.from_records(zattrs)[["sonde_ID", "sonde_time"]]
    df["sonde_time"] = pd.to_datetime(df["sonde_time"])
    return df.sort_values("sonde_time").set_index("sonde_ID").to_xarray().rename({"sonde_ID": "sonde_id", "sonde_time": "launch_time"})

def get_overpass_point(ds, target_lat, target_lon):
    import numpy as np
    from orcestra.flightplan import geod
    _, _, dist = geod.inv(ds.lon.values,
                          ds.lat.values,
                          np.full_like(ds.lon.values, target_lon),
                          np.full_like(ds.lon.values, target_lat),
                         )
    i = np.argmin(dist)
    return float(dist[i]), ds.time.values[i]
    
def plot_overpass_point(ds, target_lat, target_lon):
    import matplotlib.pyplot as plt
    d, t = get_overpass_point(ds, target_lat, target_lon)
    plt.plot(ds.lon, ds.lat, label="track")
    plt.scatter(ds.lon.isel(time=0), ds.lat.isel(time=0), marker="x", label="track starting point")
    plt.scatter(target_lon, target_lat, c="C1", label="target location")
    plt.plot([ds.lon.sel(time=t), target_lon], [ds.lat.sel(time=t), target_lat], color="C1")
    plt.legend()
    print(f"{d:.0f}m @ {t}")
    plt.show()

def get_overpass_track(a_track, b_track, a_lon="lon", a_lat="lat", b_lon="lon", b_lat="lat", optimize=True):
    """
    Extract time and distance of closest point between two tracks given as datasets to the function.
    Optionally, the lat and lon coordinate names of the respective datasets can be specified
    if they are different from the default "lat" and "lon".
    """
    from orcestra.flightplan import geod
    a = a_track.sel(time=slice(*b_track.time[[0, -1]]))
    b = b_track.interp(time=a.time.astype(b_track.time.dtype))
    _, _, dist = geod.inv(b[b_lon], b[b_lat], a[a_lon], a[a_lat])
    i = dist.argmin()

    if optimize:
        import numpy as np
        from scipy.optimize import minimize

        t_guess = a.time.values[i]
        t_unit = np.timedelta64(1000_000_000, "ns")

        _a = a.assign_coords(time=(a.time - t_guess) / t_unit)
        _b = b.assign_coords(time=(b.time - t_guess) / t_unit)

        def cost(t):
            t = float(t[0])
            a = _a.interp(time=t, method="linear")
            b = _b.interp(time=t, method="linear")
            _, _, dist = geod.inv(b[b_lon], b[b_lat], a[a_lon], a[a_lat])
            return dist

        res = minimize(cost, 0., method="Nelder-Mead")
        t = float(res.x[0])
        a = _a.interp(time=t, method="linear")
        b = _b.interp(time=t, method="linear")
        _, _, dist = geod.inv(b[b_lon], b[b_lat], a[a_lon], a[a_lat])
        return float(dist), t_guess + t * t_unit
    else:
        return float(dist[i]), a.time.values[i]


def flight_id2datestr(flight_id):
    d = flight_id.split("-")[1][:-1]
    return d[:4] + "-" + d[4:6] + "-" + d[6:]


def get_ec_track(flight_id, ds):
    import orcestra.sat
    import numpy as np
    import warnings
    takeoff, landing, _ = get_takeoff_landing(flight_id, ds)
    valid_date = takeoff.astype("datetime64[D]")
    issue_dates = [valid_date - np.timedelta64(i, 'D') for i in range(0, 6)]
    if np.datetime64(valid_date) > np.datetime64("2024-11-01T00:00:00"):
        roi = "EUR"
    elif np.datetime64(valid_date) >= np.datetime64("2024-09-07T00:00:00"):
        roi = "BARBADOS" # region of interest
    else:
        roi = "CAPE_VERDE"
    for issue_date in issue_dates:
        try:
            ec_track = orcestra.sat.SattrackLoader(
                "EARTHCARE", issue_date, kind="PRE",roi=roi
            ).get_track_for_day(valid_date).sel(time=slice(takeoff, landing))
            break
        except:
            warnings.warn("No sattrack forecast issued on flightday, " +
                          "I will use an older sattrack forecast!")
            continue
    return ec_track


def ec_event(ds, ec_track, ec_remarks=None):
    dist, time = get_overpass_track(ds, ec_track)
    return {"name": "EC meeting point",
            "time": to_dt(time),
            "kinds": ["ec_underpass"],
            "distance": round(dist), #rounding to full meters
            "remarks": ec_remarks or [],
           }

def pace_event(ds, pace_track, remarks=None):
    dist, time = get_overpass_track(ds, pace_track)
    return {"name": "PACE meeting point",
            "time": to_dt(time),
            "kinds": ["pace_underpass"],
            "distance": round(dist), #rounding to full meters
            "remarks": remarks or [],
           }


def meteor_event(ds, meteor_track, seg=None, name=None, remarks=None):
    if seg: ds = ds.sel(time=parse_segment(seg)["slice"])
    dist, meeting_time = get_overpass_track(ds, meteor_track)
    return {"name": name or "METEOR overpass",
            "time": to_dt(meeting_time),
            "kinds": ["meteor_overpass"],
            "distance": round(dist), #rounding to full meters
            "remarks": remarks or [],
            "meteor_lat": float(meteor_track.interp(time=[meeting_time], method="linear").lat[0].values),
            "meteor_lon": float(meteor_track.interp(time=[meeting_time], method="linear").lon[0].values),
           }


def target_event(ds, target=None, target_lat=None, target_lon=None,
                 seg=None, name=None, kinds=None, remarks=None):
    if target=="BCO":
        from orcestra.flightplan import bco
        target_lat, target_lon = bco.lat, bco.lon
        target_name = "BCO overpass"
        target_kinds = ["bco_overpass"]

    elif target=="CVAO":
        from orcestra.flightplan import mindelo
        target_lat, target_lon = mindelo.lat, mindelo.lon
        target_name = "CVAO overpass"
        target_kinds = ["cvao_overpass"]

    elif target=="MIM":
        target_lat, target_lon = 48.14778, 11.57333
        target_name = "MIM overpass"
        target_kinds = ["mim_overpass"]

    elif (target is None) and ((target_lat is None) or (target_lon is None)):
        print("You need to specify either a target, i.e. BCO, CVAO, MIM or a target_lat and target_lon")
        return
    else:
        target_name = "target meeting point"
        target_kinds = ["point_overpass"]
    
    if seg: ds = ds.sel(time=parse_segment(seg)["slice"])
    dist, time = get_overpass_point(ds, target_lat, target_lon)

    return {"name": name or target_name,
            "time": to_dt(time),
            "kinds": kinds or target_kinds,
            "distance": round(dist), #rounding to full meters
            "remarks": remarks or [],
           }


def fit_circle(lat, lon):
    """
    Given a sequence of WGS84-Coordinates (lat and lon) on points along a circular path,
    this function determines the center and radius of that circle.
    """
    from orcestra.flightplan import geod
    from scipy.optimize import minimize
    import numpy as np

    lat = np.asarray(lat)
    lon = np.asarray(lon)

    clat = np.mean(lat)
    clon = np.mean(lon)

    def cost(x):
        clat, clon = x
        _, _, d = geod.inv(lon, lat, np.full_like(lon, clon), np.full_like(lat, clat))
        return np.std(d)

    res = minimize(cost, [clat, clon], method="Nelder-Mead")
    clat, clon = res.x
    _, _, d = geod.inv(lon, lat, np.full_like(lon, clon), np.full_like(lat, clat))
    return float(clat), float(clon), float(np.mean(d))

def ransac_fit_circle(lat, lon, distance_range=1e3, n=100):
    """
    Given a sequence of WGS84-Coordinates (lat and lon) on points along a circular path,
    this function determines the center and radius of that circle.
    """
    import numpy as np
    from orcestra.flightplan import geod

    lat = np.asarray(lat)
    lon = np.asarray(lon)
    rng = np.random.default_rng(12345)

    samples = []
    for _ in range(n):
        idxs = rng.choice(len(lat), 3, replace=False)

        clat, clon, radius = fit_circle(lat[idxs], lon[idxs])

        _, _, d = geod.inv(lon, lat, np.full_like(lon, clon), np.full_like(lat, clat))
        n_in = np.sum(np.abs(radius - d) <= distance_range)

        samples.append((n_in, clat, clon, radius))

    n_in_good, clat, clon, radius = sorted(samples)[-1]
    _, _, d = geod.inv(lon, lat, np.full_like(lon, clon), np.full_like(lat, clat))
    good = np.abs(radius - d) <= distance_range
    return fit_circle(lat[good], lon[good])


def _attach_circle_fit(segment, ds):
    if "circle" not in segment["kinds"]:
        return segment

    cdata = ds.sel(time=segment["slice"])
    clat, clon, radius = ransac_fit_circle(cdata.lat.values, cdata.lon.values)
    return {
        **segment,
        "clat": clat,
        "clon": clon,
        "radius": radius,
    }


def attach_circle_fit(segments, ds):
    return [_attach_circle_fit(s, ds) for s in segments]


def to_dt(dt64):
    import pandas as pd
    return pd.Timestamp(dt64).to_pydatetime(warn=False)

def wgs84_altitude_takeoff(flight_id, ds):
    import numpy as np
    if (ds.time[0].values < np.datetime64("2024-08-10T00:00:00") or                     # Transfer flight to Sal
        (ds.time[0].values > np.datetime64("2024-11-01T00:00:00") and "b" in flight_id) # Two November flights
        ):
        wgs84_altitude_takeoff = 681   #Memmingen
    elif ds.time[0].values > np.datetime64("2024-11-01T00:00:00"):                       # All other November flights
        wgs84_altitude_takeoff = 630   #Oberpfaffenhofen
    elif (ds.time[0].values >= np.datetime64("2024-08-10T00:00:00") and                  
          ds.time[0].values < np.datetime64("2024-09-07T00:00:00")
         ):
        wgs84_altitude_takeoff = 90    #Sal
    elif ds.time[0].values >= np.datetime64("2024-09-07T00:00:00"):
        wgs84_altitude_takeoff = 9     #Barbados
    return wgs84_altitude_takeoff

def wgs84_altitude_landing(flight_id, ds):
    import numpy as np
    if ds.time[-1].values < np.datetime64("2024-09-05T00:00:00"):
        wgs84_altitude_landing = 90    #Sal
    elif (ds.time[-1].values >= np.datetime64("2024-09-05T00:00:00") and
          ds.time[-1].values < np.datetime64("2024-09-29T00:00:00")
         ):
        wgs84_altitude_landing = 9     #Barbados
    elif ds.time[-1].values > np.datetime64("2024-11-01T00:00:00"):                     # All other November flights
        wgs84_altitude_landing = 630   #Oberpfaffenhofen
    elif ds.time[-1].values >= np.datetime64("2024-09-30T00:00:00") and ds.time[-1].values <= np.datetime64("2024-09-30T23:59:59"):                          # Transfer back from Barbados
        wgs84_altitude_landing = 681   #Memmingen
    return wgs84_altitude_landing


def get_takeoff_landing(flight_id, ds, min_duration=None):
    """
    Detect take-off and landing for the airport on Sal and Barbados
    which are located at about 89m and 8m above WGS84 respectively.
    """
    import numpy as np

    if min_duration is None:
        min_duration = np.timedelta64(15, "m")

    takeoff_alt = wgs84_altitude_takeoff(flight_id, ds)
    landing_alt = wgs84_altitude_landing(flight_id, ds)    
    takeoff = ds["time"].where(ds.alt > takeoff_alt, drop=True)[0].values
    if len(ds["time"].where((ds.alt <= landing_alt) & (ds.time > takeoff), drop=True)) == 0: # handle exception of missing BAHAMAS data at end of flight
        landing = ds["time"][-1].values
    else:
        landing = ds["time"].where((ds.alt <= landing_alt) & (ds.time > takeoff + min_duration), drop=True)[0].values
    duration = (landing - takeoff).astype("timedelta64[m]").astype(int)
    return takeoff, landing, duration

def segment_hash(segment):
    import hashlib
    return hashlib.sha256(f"{segment.start}+{segment.stop}".encode("ascii")).hexdigest()[-4:]

def event_hash(event):
    import hashlib
    return hashlib.sha256(f"{event["time"]}".encode("ascii")).hexdigest()[-4:]

def parse_segment(segment):
    if isinstance(segment, tuple):
        seg = {
            "slice": segment[0],
        }
        if len(segment) >= 2:
            seg["kinds"] = segment[1]
        if len(segment) >= 3:
            seg["name"] = segment[2]
        if len(segment) >= 4:
            seg["remarks"] = segment[3]
        if len(segment) >= 5:
            seg["extra_sondes"] = segment[4]
    elif isinstance(segment, dict):
        return segment
    else:
        seg = {"slice": segment}
    return seg

def to_yaml(platform, flight_id, ds, segments, events):
    segments = attach_circle_fit([parse_segment(s) for s in segments], ds)
    takeoff, landing, _ = get_takeoff_landing(flight_id, ds)
    return {"mission": "ORCESTRA",
            "platform": platform,
            "flight_id": flight_id,
            "takeoff": to_dt(takeoff),
            "landing": to_dt(landing),
            "events": [{"event_id": f"{flight_id}_{event_hash(e)}",
                        "name": None,
                        "time": to_dt(e["time"]),
                        "kinds": [],
                        "remarks": [],
                        **{k: v for k, v in e.items() if k not in ["event_id", "time"]},
                        } for e in events],
            "segments": [{"segment_id": f"{flight_id}_{segment_hash(s["slice"])}",
                          "name": None,
                          "start": to_dt(s["slice"].start),
                          "end": to_dt(s["slice"].stop),
                          "kinds": [],
                          "remarks": [],
                          **{k: v for k, v in s.items() if k not in ["segment_id", "start", "end", "slice"]},
                         } for s in segments]
           }
