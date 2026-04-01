---
jupyter:
  jupytext:
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.16.4
  kernelspec:
    display_name: Python 3 (ipykernel)
    language: python
    name: python3
---

# Flight segmentation HALO-20240928a

```python
import matplotlib
import yaml
import hvplot.xarray
import xarray as xr
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from navdata import get_navdata_HALO
from utils import *

from orcestra.flightplan import bco, mindelo
cvao = mindelo
```

```python
platform = "HALO"
flight_id = "HALO-20240928a"
```

## Loading data
### Get HALO position and attitude

```python
ds = get_navdata_HALO(flight_id)
```

### Get dropsonde launch times

```python
drops = get_sondes_l2(flight_id)
ds_drops = ds.sel(time=drops.launch_time, method="nearest") \
             .swap_dims({"sonde_id": "time"}) \
             .sortby("time")
```

### Defining takeoff and landing
On Barbads, the airport runway plus bumps make HALO move between 7.8-8m above WGS84, on Sal between 88.2-88.4m above WGS84. We therefore define the flight time such that altitude must be above 9m on Barbados and 90m on Sal.

```python
takeoff, landing, duration = get_takeoff_landing(flight_id, ds)
print("Takeoff time: " + str(takeoff))
print("Landing time: " + str(landing))
print(f"Flight duration: {int(duration / 60)}:{int(duration % 60)}")
```

### Get EC track and EC meeting point

```python
ec_track = get_ec_track(flight_id, ds)
dist_ec, t_ec = get_overpass_track(ds, ec_track)
```

### Get PACE track
**loading the PACE track for the first time takes 6-7 minutes!**
Might be worth only if the flight report states a PACE coordination. Based on your decision, choose `load_pace = True` or `load_pace = False`!

```python
load_pace = True

if load_pace:
    from get_pace import get_pace_track
    _pace_track = get_pace_track(to_dt(takeoff), to_dt(landing))
    
    pace_track = _pace_track.where(
            (_pace_track.lat > ds.lat.min()-2) & (_pace_track.lat < ds.lat.max()+2) &
            (_pace_track.lon > ds.lon.min()-2) & (_pace_track.lon < ds.lon.max()+2),
            drop=True)
else:
    pace_track = None
```

### Get METEOR track
select maybe only the track from the respective flight day

```python
from orcestra.meteor import get_meteor_track

meteor_track = get_meteor_track().sel(time=slice(takeoff, landing))
```

## Overview plot: HALO track, EC meeting point, and dropsonde locations

```python
plt.plot(ds.lon.sel(time=slice(takeoff, landing)), ds.lat.sel(time=slice(takeoff, landing)), label="HALO track")
plt.scatter(ds_drops.lon, ds_drops.lat, s=10, c="k", label="dropsondes")
plt.plot(ec_track.lon, ec_track.lat, c='C1', ls='dotted')
plt.plot(ds.lon.sel(time=t_ec, method="nearest"), ds.lat.sel(time=t_ec, method="nearest"), marker="*", ls=":", label="EC meeting point")
if pace_track: plt.plot(pace_track.lon, pace_track.lat, c="C2", ls=":", label="PACE track")
plt.plot(meteor_track.lon, meteor_track.lat, c="C4", ls="-.", label="METEOR track")
plt.xlabel("longitude / °")
plt.ylabel("latitude / °")
plt.legend();
```

## Interactive plots

```python
ds["alt"].hvplot()
```

```python
ds["roll"].hvplot()
```

```python
ds["heading"].hvplot()
```

# Segments

defined as a tuple of time slice (`start`, `end`) , segment `kind`, `name`, `remarks`.

* in case of irregularities within a circle, 1 sec before the first and after the last sonde are chosen as start and end times
* use the list of `remarks` to state any deviations, also with respective times

Alternatively, you can also define the segments as dictionaries which also allows to add further attributes to single segments, e.g. a `radius` to a `circle` segment. At the end of the following code block all segments will be normalized by the `parse_segments` function.

```python
ac1 = (
    slice("2024-09-28T10:49:42", "2024-09-28T11:19:46"),
    ["straight_leg", "ascent"],
    "ferry_eastward_ascent_1",
    [],
)

sl1a = (
    slice("2024-09-28T11:19:46", "2024-09-28T12:22:42"),
    ["straight_leg"],
    "ferry_eastward_1",
    ["irregularity: roll angle spike of -5.75 degree at 11:37:15",
    "irregularity: constant nonzero roll angle of about 0.75 degree"]
)

ac2 = (
    slice("2024-09-28T12:22:42", "2024-09-28T12:26:46"),
    ["straight_leg", "ascent"],
    "ferry_eastward_ascent_2",
    ["irregularity: constant nonzero roll angle of about 0.75 degree"]
)

sl1c = (
    slice("2024-09-28T12:26:46", "2024-09-28T12:32:49"),
    ["straight_leg"],
    "ferry_eastward_2",
    ["irregularity: constant nonzero roll angle of about 0.75 degree"],
)

c1 = (
    slice("2024-09-28T12:34:43", "2024-09-28T13:32:02"),
    ["circle", "circle_clockwise"],
    "circle_east",
    ["irregularity: early start due to first sonde. Roll angle stable after 12:35:03."],
)

sl2 = (
    slice("2024-09-28T13:35:30", "2024-09-28T13:39:35"),
    ["straight_leg"],
    "ferry_towards_circle_mid_east",
    [],
)

c2 = (
    slice("2024-09-28T13:42:16", "2024-09-28T14:37:51"),
    ["circle", "circle_clockwise"],
    "circle_mid_east",
    ["irregularity: early start due to first sonde. Roll angle stable after 13:42:38.",
     "irregularity: few height level jumps by up to 30m and concurrent roll angle change by about 1deg",
    ],
    [str(ds_drops.sel(time="2024-09-28T14:48:34").sonde_id.values),
     str(ds_drops.sel(time="2024-09-28T14:55:26").sonde_id.values)],
)

sl3a = (
    slice("2024-09-28T14:41:42", "2024-09-28T14:55:27"),
    ["straight_leg"],
    "ferry_towards_circle_mid_west_1",
    ["irregularity: turbulence with roll angle deviations up to +-1.4 deg",
     "includes two dropsonde launches"],
)

sl3b = (
    slice("2024-09-28T14:55:27", "2024-09-28T15:01:38"),
    ["straight_leg", "ascent"],
    "ferry_towards_circle_mid_west_ascent",
    [],
)

sl3c = (
    slice("2024-09-28T15:01:38", "2024-09-28T15:24:30"),
    ["straight_leg"],
    "ferry_towards_circle_mid_west_2",
    ["includes three dropsonde launches"],
)

c3 = (
    slice("2024-09-28T15:27:44", "2024-09-28T16:23:17"),
    ["circle", "circle_clockwise"],
    "circle_mid_west",
    [],
    [str(ds_drops.sel(time="2024-09-28T15:09:12").sonde_id.values),
     str(ds_drops.sel(time="2024-09-28T15:16:22").sonde_id.values)],
)

sl4 = (
    slice("2024-09-28T16:26:50", "2024-09-28T16:30:41"),
    ["straight_leg"],
    "ferry_towards_circle_west",
    [],
)

c4 = (
    slice("2024-09-28T16:33:57", "2024-09-28T17:28:58"),
    ["circle", "circle_clockwise"],
    "circle_mid_west_with_pace_underpass",
    ["circle path crosses PACE track"],
)

ec1 = (
    slice("2024-09-28T17:31:22", "2024-09-28T17:55:11"),
    ["straight_leg", "ec_track"],
    "ec_track_southward",
    ["includes EC underpass",
     "includes one dropsonde launch near EC underpass"]
)

sl5a = (
    slice("2024-09-28T17:58:30", "2024-09-28T18:04:43"),
    ["straight_leg"],
    "ferry_towards_circle_southwest_1",
    [],
)

cal1 = (
    slice("2024-09-28T18:04:52", "2024-09-28T18:07:11"),
    ["radar_calibration_wiggle"],
    "radar_calibration_1",
    []
)

sl5b = (
    slice("2024-09-28T18:09:29", "2024-09-28T18:13:07"),
    ["straight_leg"],
    "ferry_towards_circle_southwest_2",
    [],
)

c5 = (
    slice("2024-09-28T18:15:44", "2024-09-28T19:10:07"),
    ["circle", "circle_clockwise"],
    "circle_southwest",
    ["circle path crosses PACE track"],
    [str(ds_drops.sel(time="2024-09-28T19:14:52").sonde_id.values)],
)

sl6 = (
    slice("2024-09-28T19:12:35", "2024-09-28T19:15:05"),
    ["straight_leg"],
    "ferry_northwestward_through_circle_southwest_1",
    ["includes one dropsonde launch inside circle_southwest"]
)

sl7a = (
    slice("2024-09-28T19:16:11", "2024-09-28T19:24:49"),
    ["straight_leg"],
    "ferry_northwestward_through_circle_southwest_2",
    ["leg inside circle_southwest"]
)

sl7b = (
    slice("2024-09-28T19:24:49", "2024-09-28T19:30:09"),
    ["straight_leg", "descent"],
    "ferry_northwestward_through_circle_southwest_descent",
    ["leg inside circle_southwest"]
)

sl8 = (
    slice("2024-09-28T19:30:09", "2024-09-28T19:33:47"),
    ["straight_leg"],
    "ferry_northwestward",
    [],
)

sl9 = (
    slice("2024-09-28T19:33:47", "2024-09-28T19:38:41"),
    ["straight_leg", "descent"],
    "ferry_northwestward_descent_1",
    [],
)

cal2 = (
    slice("2024-09-28T19:39:41", "2024-09-28T19:42:08"),
    ["radar_calibration_dive"],
    "radar_calibration_2",
    [],
)

sl10 = (
    slice("2024-09-28T19:42:08", "2024-09-28T19:47:34"),
    ["straight_leg", "descent"],
    "ferry_northwestward_descent_2",
    [],
)

sl11 = (
    slice("2024-09-28T19:48:08", "2024-09-28T19:53:48"),
    ["straight_leg", "descent"],
    "ferry_northwestward_descent_3",
    [],
)
# add all segments that you want to save to a yaml file later to the below list

segments = [parse_segment(s) for s in [ac1, sl1a, ac2, sl1c, c1, sl2, c2, sl3a, sl3b, sl3c, c3, sl4, c4,
                                       ec1, sl5a, cal1, sl5b, c5, sl6, sl7a, sl7b, sl8,
                                       sl9, cal2, sl10, sl11]]
```

### Quick plot for working your way through the segments piece by piece
select the segment that you'd like to plot and optionally set the flag True for plotting the previous segment in your above specified list as well. The latter can be useful for the context if you have segments that are close or overlap in space, e.g. a leg crossing a circle.

```python
seg=parse_segment(sl11)
add_previous_seg = False

###########################

fig = plt.figure(figsize=(12, 5))
gs = fig.add_gridspec(2,2)
ax1 = fig.add_subplot(gs[:, 0])

# extend the segment time period by 3min before and after to check outside dropsonde or roll angle conditions
seg_drops = slice(pd.Timestamp(seg["slice"].start) - pd.Timedelta("3min"), pd.Timestamp(seg["slice"].stop) + pd.Timedelta("3min"))
ax1.plot(ds.lon.sel(time=seg_drops), ds.lat.sel(time=seg_drops), "C0")

# plot the previous segment as well as the chosen one
if add_previous_seg:
    if segments.index(seg) > 0:
        seg_before = segments[segments.index(seg) - 1]
        ax1.plot(ds.lon.sel(time=seg_before["slice"]), ds.lat.sel(time=seg_before["slice"]), color="grey")
ax1.plot(ds.lon.sel(time=seg["slice"]), ds.lat.sel(time=seg["slice"]), color="C1")

# plot dropsonde markers for extended segment period as well as for the actually defined period
ax1.scatter(ds_drops.lon.sel(time=seg_drops), ds_drops.lat.sel(time=seg_drops), c="C0")
ax1.scatter(ds_drops.lon.sel(time=seg["slice"]), ds_drops.lat.sel(time=seg["slice"]), c="C1")

ax2 = fig.add_subplot(gs[0, 1])
ds["alt"].sel(time=seg_drops).plot(ax=ax2, color="C0")
ds["alt"].sel(time=seg["slice"]).plot(ax=ax2, color="C1")

ax3 = fig.add_subplot(gs[1, 1])
ds["roll"].sel(time=seg_drops).plot(ax=ax3, color="C0")
ds["roll"].sel(time=seg["slice"]).plot(ax=ax3, color="C1")

#Check dropsonde launch times compared to the segment start and end times
print(f"Segment time: {seg["slice"].start} to {seg["slice"].stop}")
print(f"Dropsonde launch times: {ds_drops.time.sel(time=seg_drops).values}")
```

### Identify visually which straight_leg segments lie on EC track

```python
seg = parse_segment(sl7a)
plt.plot(ds.lon.sel(time=slice(takeoff, landing)), ds.lat.sel(time=slice(takeoff, landing)))
plt.plot(ds.lon.sel(time=seg["slice"]), ds.lat.sel(time=seg["slice"]), color='red', label="selected segment", zorder=10)
plt.scatter(ds_drops.lon, ds_drops.lat, s=10, c="k", label="dropsondes")
plt.plot(ec_track.lon, ec_track.lat, c='C1', ls='dotted')
plt.plot(ds.lon.sel(time=t_ec, method="nearest"), ds.lat.sel(time=t_ec, method="nearest"),
         marker="*", ls=":", label="EC meeting point", zorder=20)
if pace_track: plt.plot(pace_track.lon, pace_track.lat, c="C2", ls=":", label="PACE track")
plt.xlabel("longitude / °")
plt.ylabel("latitude / °")
plt.legend();
```

## Events
events are different from segments in having only **one** timestamp. Examples are the usual "EC meeting points" or station / ship overpasses. In general, events include a mandatory `event_id` and `time`, as well as optional statements on `name`, a list of `kinds`, the `distance` in meters, and a list of `remarks`. Possible `kinds`include:
- `ec_underpass`
- `meteor_overpass`
- `bco_overpass`
- `cvao_overpass`

The `event_id` will be added when saving it to YAML.

The EC underpass event can be added to a list of events via the function `ec_event`.

```python
events = [
    ec_event(ds, ec_track),
]
events
```

## Save segments and events to YAML file

```python
yaml.dump(to_yaml(platform, flight_id, ds, segments, events),
          open(f"../flight_segment_files/{flight_id}.yaml", "w"),
          sort_keys=False)
```

## Import YAML and test it

```python
flight = yaml.safe_load(open(f"../flight_segment_files/{flight_id}.yaml", "r"))
kinds = set(k for s in flight["segments"] for k in s["kinds"])
kinds
```

Print circle segments with extra sondes

```python
[s for s in flight["segments"] if ("circle" in s["kinds"] and "extra_sondes" in s.keys())]
```

Plot all sondes related to a circle segment indetified by it's id

```python
seg = [s for s in flight["segments"] if s["segment_id"]=="HALO-20240928a_8cd2"][0]
plt.scatter(ds_drops.sel(time=slice(seg["start"], seg["end"])).lon,
         ds_drops.sel(time=slice(seg["start"], seg["end"])).lat)
if "extra_sondes" in seg.keys():
    plt.scatter(ds_drops.swap_dims({"time": "sonde_id"}).sel(sonde_id=seg["extra_sondes"]).lon,
                ds_drops.swap_dims({"time": "sonde_id"}).sel(sonde_id=seg["extra_sondes"]).lat)
```

```python
fig, ax = plt.subplots()

for k, c in zip(['straight_leg', 'circle', "radar_calibration_wiggle", "radar_calibration_dive"], ["C0", "C1", "C3", "C4"]):
    for s in flight["segments"]:
        if k in s["kinds"]:
            t = slice(s["start"], s["end"])
            ax.plot(ds.lon.sel(time=t), ds.lat.sel(time=t), c=c, label=s["name"])
ax.set_xlabel("longitude / °")
ax.set_ylabel("latitude / °");
```

### Check circle radius

```python
from orcestra.flightplan import LatLon, FlightPlan, IntoCircle

for s in flight["segments"]:
    if "circle" not in s["kinds"]: continue
    d = ds.sel(time=slice(s["start"], s["end"]))
    start = LatLon(float(d.lat[0]), float(d.lon[0]), label="start")
    center = LatLon(s["clat"], s["clon"], label="center")
    FlightPlan([start, IntoCircle(center, s["radius"], 360)]).preview()
    print(f"Radius: {round(s["radius"])} m")
    plt.plot(d.lon, d.lat, label="HALO track")
    plt.legend()
```

```python

```
