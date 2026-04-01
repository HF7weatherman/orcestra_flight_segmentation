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

# Flight segmentation HALO-20240825a

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
flight_id = "HALO-20240825a"
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
load_pace = False

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

```python jupyter={"source_hidden": true}
ds["heading"].hvplot()
```

```python
ds["roll"].hvplot()
```

## Segments

defined as a tuple of time slice (`start`, `end`) , segment `kind`, `name`, `remarks`.

* in case of irregularities within a circle, 1 sec before the first and after the last sonde are chosen as start and end times
* use the list of `remarks` to state any deviations, also with respective times

Alternatively, you can also define the segments as dictionaries which also allows to add further attributes to single segments, e.g. a `radius` to a `circle` segment. At the end of the following code block all segments will be normalized by the `parse_segments` function.

```python
seg1 = (
    slice("2024-08-25T09:18:00", "2024-08-25T09:44:45"),
    ["straight_leg", "ascent"],
    "ferry_southwestward_ascent",
    [],
)

seg2 = (
    slice("2024-08-25T09:44:46", "2024-08-25T09:55:57"),
    ["straight_leg"],
    "ferry_southwestward_1",
    [],
)

seg3 = (
    slice("2024-08-25T09:56:30", "2024-08-25T10:28:42"),
    ["straight_leg"],
    "ferry_southwestward_2",
    [],
)

seg4 = (
    slice("2024-08-25T10:30:15", "2024-08-25T10:53:01"),
    ["straight_leg", "ec_track"],
    "ec_track_southward_1",
    [],
)

seg5 = (
    slice("2024-08-25T10:54:07", "2024-08-25T11:10:40"),
    ["straight_leg", "ec_track"],
    "ec_track_southward_2",
    [],
)

seg6 = (
    slice("2024-08-25T11:12:48", "2024-08-25T11:45:49"),
    ["straight_leg", "ec_track"],
    "ec_track_southward_through_circle_south",
    ["irregularity: turbulence up to plus/minus 2.6 degree roll angle"],
)

seg7 = (
    slice("2024-08-25T11:56:28", "2024-08-25T12:52:34"),
    ["circle", "circle_counterclockwise"],
    "circle_south",
    [],
    [str(ds_drops.sel(time="2024-08-25T13:02:54").sonde_id.values)],
)

seg8 = (
    slice("2024-08-25T12:55:30", "2024-08-25T13:16:20"),
    ["straight_leg", "ec_track"],
    "ec_track_northward_through_circle_south",
    [],
)

seg9 = (
    slice("2024-08-25T13:18:30", "2024-08-25T14:14:36"),
    ["circle", "circle_counterclockwise"],
    "circle_mid",
    [],
)

seg10 = (
    slice("2024-08-25T14:18:06", "2024-08-25T14:22:26"),
    ["straight_leg", "ec_track"],
    "ec_track_northward_through_circle_mid",
    [],
)

seg11 = (
    slice("2024-08-25T14:22:26", "2024-08-25T14:27:07"),
    ["straight_leg", "ascent", "ec_track"],
    "ec_track_northward_through_circle_mid_ascent",
    [],
)

seg12 = (
    slice("2024-08-25T14:27:07", "2024-08-25T14:39:07"),
    ["straight_leg", "ec_track"],
    "ec_track_northward_1",
    [],
)

seg13 = (
    slice("2024-08-25T14:41:41", "2024-08-25T15:36:41"),
    ["circle", "circle_counterclockwise"],
    "circle_north",
    [],
)

seg14 = (
    slice("2024-08-25T15:40:17", "2024-08-25T16:36:51"),
    ["straight_leg", "ec_track"],
    "ec_track_northward_2",
    ["irregularity: roll angle of about 1 degree between 15:45:28 and 15:53:13",
    "includes EC meeting point"],
)

seg15 = (
    slice("2024-08-25T16:38:52", "2024-08-25T16:53:14"),
    ["straight_leg"],
    "ferry_eastward_1",
    [],
)

seg16 = (
    slice("2024-08-25T16:55:01", "2024-08-25T17:04:45"),
    ["smart_calibration"],
    "smart_calibration_four_turns_maneuver",
    [],
)

seg17 = (
    slice("2024-08-25T17:06:00", "2024-08-25T17:33:58"),
    ["straight_leg"],
    "straight_leg_overpassing_cvao",
    ["includes CVAO overpass"],
)

seg18 = (
    slice("2024-08-25T17:34:47", "2024-08-25T17:42:49"),
    ["straight_leg"],
    "ferry_eastward_2",
    [],
)

seg19 = (
    slice("2024-08-25T17:42:49", "2024-08-25T17:53:13"),
    ["straight_leg", "descent"],
    "ferry_towards_atr_circle_descent",
    ["irregularity: slight heading adjustment between 17:46:40 and 17:48:31"],
)

seg20 = (
    slice("2024-08-25T17:56:30", "2024-08-25T18:34:32"),
    ["circle", "atr_coordination", "circle_counterclockwise"],
    "atr_circle",
    [],
)

seg21 = (
    slice("2024-08-25T18:39:32", "2024-08-25T18:53:35"),
    ["straight_leg", "descent"],
    "ferry_northward_descent",
    [],
)

seg22 = (
    slice("2024-08-25T18:54:50", "2024-08-25T18:58:41"),
    ["straight_leg", "descent"],
    "ferry_descent",
    ["irregularity: tubulence up to plus/minus 2.4 degree roll angle"],
)


# add all segments that you want to save to a yaml file later to the below list
segments = [parse_segment(s) for s in [seg1, seg2, seg3, seg4, seg5, seg6, seg7, seg8, seg9, seg10, seg11, seg12, seg13, seg14, seg15, seg16, seg17, seg18, seg19, seg20, seg21, seg22]]
```

### Quick plot for working your way through the segments piece by piece
select the segment that you'd like to plot and optionally set the flag True for plotting the previous segment in your above specified list as well. The latter can be useful for the context if you have segments that are close or overlap in space, e.g. a leg crossing a circle.

```python
seg=parse_segment(seg22)
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
seg = parse_segment(seg22)
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
get_overpass_point(ds, cvao.lat, cvao.lon)
```

```python
events = [
    ec_event(ds, ec_track),
    target_event(ds, target = "CVAO")
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

Print circle segments

```python
[s for s in flight["segments"] if "circle" in s["kinds"]]
```

Plot all sondes related to a circle segment indetified by it's id

```python
seg = [s for s in flight["segments"] if s["segment_id"]=="HALO-20240825a_7edc"][0]
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

```python

```
