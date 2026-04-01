---
jupyter:
  execution:
    timeout: 60
  jupytext:
    notebook_metadata_filter: execution
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

# Flight segmentation HALO-20240919a

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
flight_id = "HALO-20240919a"
```

## Loading data
### Get HALO position and attitude

```python
ds = get_navdata_HALO(flight_id)
```

### Get dropsonde launch times

```python
drops = get_sondes_l2(flight_id)
ds_drops = ds.sel(time=drops.launch_time, method="nearest").swap_dims({"sonde_id": "time"})
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
dist_pace, t_pace = get_overpass_track(ds, pace_track)
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
if pace_track:
    plt.plot(pace_track.lon, pace_track.lat, c="C2", ls=":")
    plt.plot(ds.lon.sel(time=t_pace, method="nearest"), ds.lat.sel(time=t_pace, method="nearest"),
         marker="*", ls=":", label="PACE meeting point", zorder=20)
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

## Segments

defined as a tuple of time slice (`start`, `end`) , segment `kind`, `name`, `remarks`.

* in case of irregularities within a circle, 1 sec before the first and after the last sonde are chosen as start and end times
* use the list of `remarks` to state any deviations, also with respective times

Alternatively, you can also define the segments as dictionaries which also allows to add further attributes to single segments, e.g. a `radius` to a `circle` segment. At the end of the following code block all segments will be normalized by the `parse_segments` function.

```python
ac1 = (
    slice("2024-09-19 11:05:00", "2024-09-19 11:33:39"),
    ["straight_leg", "ascent"],
    "ferry_eastward_ascent",
    [],
) 

sl1 = (
    slice("2024-09-19 11:33:39", "2024-09-19 12:32:40"),
    ["straight_leg", "meteor_coordination"],    
    "ferry_eastward",
    ["includes Meteor overpass"],
)

c1 = (
    slice("2024-09-19 12:35:30", "2024-09-19 13:30:35"),
    ["circle", "circle_counterclockwise"],
    "circle_east",
    ["irregularity: turbulence 12:32:30 - 12:48:00 with up to +-25 deg roll angle deviation"],
)

sl2 = (
    slice("2024-09-19 13:36:25", "2024-09-19 13:56:00"),
    ["straight_leg", "meteor_coordination"],
    "straight_leg_through_circle_mid",
    ["includes Meteor overpass"],
)     

c2 = (
    slice("2024-09-19 13:58:32", "2024-09-19 14:53:20"),
    ["circle", "circle_counterclockwise", "meteor_coordination"],
    "circle_mid",
    [],
    [str(ds_drops.sel(time="2024-09-19T13:46:42").sonde_id.values),
     str(ds_drops.sel(time="2024-09-19T13:52:12").sonde_id.values)],
)

catr = (
    slice("2024-09-19 15:03:25", "2024-09-19 15:33:36"),
    ["circle", "circle_counterclockwise"],
    "circle_mid_small",
    ["smaller radius due to time limitations"],
)

sl3a = (
    slice("2024-09-19 15:47:30", "2024-09-19 16:27:00"),
    ["straight_leg"],
    "pace_track_northward",
    ["irregularity: constant non-zero roll angle of about 1 deg between 16:15:11 and 16:21:16",
    "includes PACE meeting point at 16:23:21"],
)

c4 = (
    slice("2024-09-19 16:30:13", "2024-09-19 17:25:15"),
    ["circle", "circle_clockwise"],
    "circle_north",
    [],
    [str(ds_drops.sel(time="2024-09-19T16:10:29").sonde_id.values),
     str(ds_drops.sel(time="2024-09-19T16:19:36").sonde_id.values),
     str(ds_drops.sel(time="2024-09-19T17:34:14").sonde_id.values),
     str(ds_drops.sel(time="2024-09-19T17:41:46").sonde_id.values)],
)

ec1 = (
    slice("2024-09-19 17:30:00", "2024-09-19 17:58:00"),
    ["straight_leg", "ec_track"],
    "ec_track_southward",
    ["irregularity: turbulence 17:36:30 - 17:38:00 with up to +-7.7 deg roll angle deviation",
     "includes EC meeting point"],
)

cal = (
    slice("2024-09-19 17:58:30", "2024-09-19 18:00:58"),
    ["radar_calibration_wiggle"],
    "radar_calibration",
    [],
)

c5 = (
    slice("2024-09-19 18:04:55", "2024-09-19 19:04:15"),
    ["circle", "circle_clockwise"],
    "circle_west",
    [],
    [str(ds_drops.sel(time="2024-09-19T19:11:11").sonde_id.values),
     str(ds_drops.sel(time="2024-09-19T19:17:21").sonde_id.values)],
)

sl4 = (
    slice("2024-09-19 19:06:00", "2024-09-19 19:14:25"),
    ["straight_leg"],
    "straight_leg_through_circle_west",
    [],
)

sl5 = (
    slice("2024-09-19 19:15:00", "2024-09-19 19:24:20"),
    ["straight_leg"],
    "ferry_westward",
    [],
)

dc1 = (
    slice("2024-09-19 19:24:20", "2024-09-19 19:35:49"),
    ["straight_leg", "descent"],
    "ferry_westward_descent",
    [],
)

sl6 = (
    slice("2024-09-19 19:48:08", "2024-09-19 19:51:23"),
    ["straight_leg"],
    "ferry_westward_towards_airport",
    [],
)

# add all segments that you want to save to a yaml file later to the below list
segments = [parse_segment(s) for s in [ac1, sl1, c1, sl2, c2,
                                       catr, sl3a,
                                       c4, ec1, cal, c5,
                                       sl4, sl5, dc1, sl6]]
```

### Quick plot for working your way through the segments piece by piece
select the segment that you'd like to plot and optionally set the flag True for plotting the previous segment in your above specified list as well. The latter can be useful for the context if you have segments that are close or overlap in space, e.g. a leg crossing a circle.

```python
seg=parse_segment(sl6)
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

### Identify visually which straight_leg segments lie on EC and PACE track

```python
seg = parse_segment(ec1)
plt.plot(ds.lon.sel(time=slice(takeoff, landing)), ds.lat.sel(time=slice(takeoff, landing)))
plt.plot(ds.lon.sel(time=seg["slice"]), ds.lat.sel(time=seg["slice"]), color='red', label="selected segment", zorder=10)
plt.scatter(ds_drops.lon, ds_drops.lat, s=10, c="k", label="dropsondes")
plt.plot(ec_track.lon, ec_track.lat, c='C1', ls='dotted')
plt.plot(ds.lon.sel(time=t_ec, method="nearest"), ds.lat.sel(time=t_ec, method="nearest"),
         marker="*", ls=":", label="EC meeting point", zorder=20)
if pace_track:
    plt.plot(pace_track.lon, pace_track.lat, c="C2", ls=":")
    plt.plot(ds.lon.sel(time=t_pace, method="nearest"), ds.lat.sel(time=t_pace, method="nearest"),
         marker="*", ls=":", label="PACE meeting point", zorder=20)
plt.xlabel("longitude / °")
plt.ylabel("latitude / °")
plt.legend();
```

## Events
events are different from segments in having only **one** timestamp. Examples are the usual "EC meeting points" or station / ship overpasses. In general, events include a mandatory `event_id` and `time`, as well as optional statements on `name`, a list of `kinds`, the `distance` in meters, and a list of `remarks`. Possible `kinds`include:
- `ec_underpass`
- `pace_underpass`
- `meteor_overpass`
- `bco_overpass`
- `cvao_overpass`

The `event_id` will be added when saving it to YAML.

The EC underpass event can be added to a list of events via the function `ec_event`.

```python
events = [
    meteor_event(ds, meteor_track, seg=sl1),
    meteor_event(ds, meteor_track, seg=sl2),
    pace_event(ds, pace_track),
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
```

```python
kinds = set(k for s in flight["segments"] for k in s["kinds"])
kinds
```

Print circle segments with extra sondes

```python
[s for s in flight["segments"] if ("circle" in s["kinds"] and "extra_sondes" in s.keys())]
```

Plot all sondes related to a circle segment indetified by it's id

```python
seg = [s for s in flight["segments"] if s["segment_id"]=="HALO-20240919a_69a2"][0]
plt.scatter(ds_drops.sel(time=slice(seg["start"], seg["end"])).lon,
         ds_drops.sel(time=slice(seg["start"], seg["end"])).lat)
if "extra_sondes" in seg.keys():
    plt.scatter(ds_drops.swap_dims({"time": "sonde_id"}).sel(sonde_id=seg["extra_sondes"]).lon,
                ds_drops.swap_dims({"time": "sonde_id"}).sel(sonde_id=seg["extra_sondes"]).lat)
```

```python
fig, ax = plt.subplots()

for k, c in zip(['straight_leg', 'circle', ], ["C0", "C1"]):
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
