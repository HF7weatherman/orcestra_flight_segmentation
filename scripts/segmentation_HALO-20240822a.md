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

# Flight segmentation HALO-20240822a

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
flight_id = "HALO-20240822a"
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
#plt.plot(pace_track.lon, pace_track.lat, c="C2", ls=":", label="PACE track")
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
seg1 = (
    slice("2024-08-22T11:26:37", "2024-08-22T11:29:11"),
    ["straight_leg", "ascent"],
    "ferry_ascent",
    []
)

seg2 = (
    slice("2024-08-22T11:31:15", "2024-08-22T11:52:44"),
    ["straight_leg", "ascent", "ec_track"],
    "ec_track_southward_ascent",
)

seg3 = (
    slice("2024-08-22T11:52:44", "2024-08-22T12:47:43"),
    ["straight_leg", "ec_track"],
    "ec_track_southward_1",
    ["irregularity: turbulence 12:31:55 +3.0 deg roll angle deviation"]
)

seg4 = (
    slice("2024-08-22T12:50:11", "2024-08-22T13:46:03"),
    ["circle", "circle_counterclockwise", "meteor_coordination"],
    "circle_south",
    ["bypassed Meteor at a distance of about 20km"]
)

seg5 = (
    slice("2024-08-22T13:49:45", "2024-08-22T13:53:56"),
    ["straight_leg", "ascent", "ec_track"],
    "ec_track_northward_ascent",
)

seg6 = (
    slice("2024-08-22T13:57:24", "2024-08-22T14:54:18"),
    ["circle", "circle_counterclockwise"],
    "circle_mid",
    ["irregularities: turbulence between 2024-08-22 14:19:07 and 2024-08-22 14:42:09"]
)

seg7 = (
    slice("2024-08-22T14:57:17", "2024-08-22T16:04:31"),
    ["straight_leg", "ec_track"],
    "ec_track_northward",
    ["irregularity: turbulence between 15:28:10 and 15:28:38 with +3.0 deg roll angle deviation",
    "includes EC meeting point"]
)

seg8 = (
    slice("2024-08-22T16:11:56", "2024-08-22T16:18:44"),
    ["straight_leg", "ec_track"],
    "ec_track_southward_2",
    []
)

seg9 = (
    slice("2024-08-22T16:18:44", "2024-08-22T16:26:50"),
    ["straight_leg", "ec_track", "descent"],
    "ec_track_southward_descent",
    []
)

seg10 = (
    slice("2024-08-22T16:26:50", "2024-08-22T16:28:46"),
    ["straight_leg", "ec_track"],
    "ec_track_southward_3",
    []
)

seg11 = (
    slice("2024-08-22T16:31:26", "2024-08-22T17:01:29"),
    ["circle", "circle_counterclockwise", "atr_coordination"],
    "atr_circle",
    ["potentially also of kind ATR_coordination (missing flight report)"],
)

seg12 = (
    slice("2024-08-22T17:08:06", "2024-08-22T18:02:31"),
    ["circle", "circle_counterclockwise"],
    "circle_north",
    []
)

seg13 = (
    slice("2024-08-22T18:04:28", "2024-08-22T18:24:12"),
    ["straight_leg"],
    "straight_leg_overpassing_cvao",
    []
)

seg14 = (
    slice("2024-08-22T18:26:40", "2024-08-22T18:35:08"),
    ["straight_leg"],
    "ferry_away_from_cvao",
    []
)

seg15 = (
    slice("2024-08-22T18:35:19", "2024-08-22T18:36:14"),
    ["radar_calibration_wiggle"],
    "potentially_radar_calibration (missing flight report)",
    []
)

seg16 = (
    slice("2024-08-22T18:38:46", "2024-08-22T18:45:50"),
    ["straight_leg", "descent"],
    "ferry_towards_atr_circle_descent",
    []
)

seg17 = (
    slice("2024-08-22T18:45:50", "2024-08-22T18:47:03"),
    ["straight_leg"],
    "ferry_towards_atr_circle",
    []
)

seg19 = (
    slice("2024-08-22T18:49:51", "2024-08-22T19:19:55"),
    ["circle", "circle_clockwise", "atr_coordination"],
    "atr_circle",
    ["irregularity: descent starting at 2024-08-22 19:17:56",
    "potentially also of kind ATR_coordination (missing flight report)"]
)

seg21 = (
    slice("2024-08-22T19:23:26", "2024-08-22T19:29:17"),
    ["straight_leg", "descent"],
    "ferry_towards_sal_descent_1",
    []
)

seg22 = (
    slice("2024-08-22T19:29:57", "2024-08-22T19:31:23"),
    ["straight_leg", "descent"],
    "ferry_towards_sal_descent_2",
    []
)

seg23 = (
    slice("2024-08-22T19:34:38", "2024-08-22T19:40:10"),
    ["straight_leg", "descent"],
    "ferry_towards_sal_descent_3",
    []
)

# add all segments that you want to save to a yaml file later to the below list
segments = [seg1, seg2, seg3, seg4, seg5, seg6, seg7, seg8, seg9, seg10, seg11, seg12, seg13, seg14, seg15, seg16, seg17, seg19, seg21, seg22, seg23]
```

### Quick plot for working your way through the segments piece by piece
select the segment that you'd like to plot and optionally set the flag True for plotting the previous segment in your above specified list as well. The latter can be useful for the context if you have segments that are close or overlap in space, e.g. a leg crossing a circle.

```python
seg=parse_segment(seg19)
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
seg = parse_segment(seg23)
plt.plot(ds.lon.sel(time=slice(takeoff, landing)), ds.lat.sel(time=slice(takeoff, landing)))
plt.plot(ds.lon.sel(time=seg["slice"]), ds.lat.sel(time=seg["slice"]), color='red', label="selected segment", zorder=10)
plt.scatter(ds_drops.lon, ds_drops.lat, s=10, c="k", label="dropsondes")
plt.plot(ec_track.lon, ec_track.lat, c='C1', ls='dotted')
plt.plot(ds.lon.sel(time=t_ec, method="nearest"), ds.lat.sel(time=t_ec, method="nearest"),
         marker="*", ls=":", label="EC meeting point", zorder=20)
#plt.plot(pace_track.lon, pace_track.lat, c="C2", ls=":", label="PACE track")
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
# Meteor overpass - looks more like a bypass due to the large distance...
meteor_event(ds, meteor_track)
```

```python
# CVAO overpass
get_overpass_point(ds, cvao.lat, cvao.lon)
```

```python
events = [
    ec_event(ds, ec_track),
    target_event(ds, "CVAO"),
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
