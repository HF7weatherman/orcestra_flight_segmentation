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

# Flight segmentation HALO-20240827a

```python
import matplotlib
import yaml
import hvplot.xarray
import xarray as xr
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import holoviews as hv

from navdata import get_navdata_HALO
from utils import *

from orcestra.flightplan import bco, mindelo
cvao = mindelo
```

```python
platform = "HALO"
flight_id = "HALO-20240827a"
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
t_ec
```

### Get PACE track
**loading the PACE track for the first time takes 6-7 minutes!**
Might be worth only if the flight report states a PACE coordination.

```python
# from get_pace import get_pace_track
# _pace_track = get_pace_track(to_dt(takeoff), to_dt(landing))

# pace_track = _pace_track.where(
#         (_pace_track.lat > ds.lat.min()-2) & (_pace_track.lat < ds.lat.max()+2) &
#         (_pace_track.lon > ds.lon.min()-2) & (_pace_track.lon < ds.lon.max()+2),
#         drop=True)
```

### Get METEOR track
select maybe only the track from the respective flight day

```python
from orcestra.meteor import get_meteor_track

meteor_track = get_meteor_track().sel(time=slice(takeoff, landing))
```

```python
dist_meteor, t_meteor = get_overpass_track(ds, meteor_track)
print(dist_meteor, t_meteor)
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
    slice("2024-08-27T10:04:14", "2024-08-27 10:29:27"),
    ["straight_leg", "ascent"],
    "ferry_towards_ec_track_ascent",
    [],
)

seg2 = (
    slice("2024-08-27T10:29:27", "2024-08-27T10:55:11"),
    ["straight_leg"],
    "ferry_towards_ec_track",
    ["irregularity: spike in roll angle at 10:39:42 by +4.5 degree"],
)

seg3 = (
    slice("2024-08-27T10:56:25", "2024-08-27T11:04:24"),
    ["straight_leg", "ec_track"],
    "ec_track_southward_1",
    [],
)

seg4 = (
    slice("2024-08-27T11:04:24", "2024-08-27T11:06:27"),
    ["straight_leg", "ascent", "ec_track"],
    "ec_track_southward_2",
    [],
)

seg5 = (
    slice("2024-08-27T11:06:27", "2024-08-27T11:18:02"),
    ["straight_leg", "ec_track"],
    "ec_track_southward_3",
    [],
)

seg6 = (
    slice("2024-08-27T11:18:59", "2024-08-27T11:26:12"),
    ["straight_leg"],
    "departure_from_ec_track_1",
    [],
)

seg7 = (
    slice("2024-08-27T11:26:33", "2024-08-27T11:28:34"),
    ["straight_leg"],
    "departure_from_ec_track_2",
    [],
)

seg8 = (
    slice("2024-08-27T11:31:26", "2024-08-27T11:33:30"),
    ["straight_leg"],
    "departure_from_ec_track_3",
    [],
)

seg9 = (
    slice("2024-08-27T11:33:58", "2024-08-27T11:35:56"),
    ["straight_leg"],
    "departure_from_ec_track_4",
    [],
)

seg10 = (
    slice("2024-08-27T11:38:41", "2024-08-27T11:56:44"),
    ["straight_leg", "ec_track"],
    "ec_track_southward_4", #any coordination? Why sonde?
    ["additional sonde dropped at 11:40:32"],
)

seg11 = (
    slice("2024-08-27T11:59:38", "2024-08-27T12:56:05"),
    ["circle", "circle_counterclockwise"],
    "circle_south",
)

seg12 = (
    slice("2024-08-27T12:59:25", "2024-08-27T13:03:17"),#05:41"),
    ["straight_leg", "ascent", "ec_track"],
    "ec_track_northward_ascent",
    [],
)
seg13 = (
    slice("2024-08-27T13:03:17", "2024-08-27T13:05:41"),
    ["straight_leg", "ec_track"],
    "ec_track_northward",
    [],
)

seg14 = (
    slice("2024-08-27T13:14:37", "2024-08-27T14:14:09"),
    ["circle", "circle_counterclockwise"],
    "circle_mid",
    ["irregularity: due to turbulences at 13:36:46-13:38:08 and 14:02:03-14:03:21"],
)

seg15 = (
    slice("2024-08-27T14:17:22", "2024-08-27T14:37:22"),
    ["straight_leg", "ec_track"],
    "ec_track_northward_through_circle_mid",
    ["start of BAHAMAS measurement gap: 14:37:22"],
)

seg16 = (
    slice("2024-08-27T14:50:53", "2024-08-27T15:50:27"),
    ["circle", "circle_counterclockwise"],
    "circle_north",
    ["end of BAHAMAS measurement gap: 14:57:20"],
)

seg17 = (
    slice("2024-08-27T15:59:45", "2024-08-27T16:16:37"),
    ["straight_leg", "ec_track"],
    "ec_track_northward_through_circle_north",
    ["contains EC overpass"],
)
# 1st crossing over Meteor
seg18 = (
    slice("2024-08-27T16:21:25", "2024-08-27T17:03:06"),
    ["straight_leg", "meteor_coordination"],
    "straight_leg_overpassing_meteor_1",
    [],
)

# 2nd crossing over Meteor
seg19 = (
    slice("2024-08-27T17:09:09", "2024-08-27T17:21:24"),
    ["straight_leg", "meteor_coordination"],
    "straight_leg_overpassing_meteor_2",
    ["sonde dropped at 17:13:41"],
)

# 3rd crossing over Meteor
seg20 = (
    slice("2024-08-27T17:28:06", "2024-08-27T17:33:37"),
    ["straight_leg", "meteor_coordination"],
    "straight_leg_overpassing_meteor_3",
    [],
)

seg21 = (
    slice("2024-08-27T17:33:37", "2024-08-27T17:39:30"),
    ["straight_leg", "descent"],
    "ferry_towards_atr_circle_descent",
    [],
)

seg22 = (
    slice("2024-08-27T17:43:57", "2024-08-27T18:19:07"),
    ["circle", "atr_coordination", "circle_counterclockwise"],
    "atr_circle",
    ["sonde failures"],
)

seg23 = (
    slice("2024-08-27T18:37:50", "2024-08-27T18:48:54"),
    ["straight_leg"],
    "ferry_towards_sal",
    [],
)

seg24 = (
    slice("2024-08-27T18:54:20", "2024-08-27T19:03:33"),
    ["straight_leg", "descent"],
    "ferry_towards_sal_descent_1",
    [],
)

seg25 = (
    slice("2024-08-27T19:04:09", "2024-08-27T19:08:18"),
    ["straight_leg", "descent"],
    "ferry_towards_sal_descent_2",
    [],
)


# add all segments that you want to save to a yaml file later to the below list
segments = [parse_segment(s) for s in [seg1, seg2, seg3, seg4, seg5, seg6, seg7, seg8, 
                                       seg9, seg10, seg11, seg12, seg13, seg14, seg15, seg16, seg17,
                                       seg18, seg19, seg20, seg21, seg22, seg23, 
                                       seg24, seg25]]
```

### Quick plot for working your way through the segments piece by piece
select the segment that you'd like to plot and optionally set the flag True for plotting the previous segment in your above specified list as well. The latter can be useful for the context if you have segments that are close or overlap in space, e.g. a leg crossing a circle.

```python
seg=parse_segment(seg14)
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
seg = parse_segment(seg7)
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

### Meteor coordination
How far was the Meteor away from the HALO track?
Overpasses happened within three consecutive straight legs before the ATR coodination circle.


#### Plot Meteor overpasses

```python
for s in [seg18, seg19, seg20]:
    d = ds.sel(time=parse_segment(s)["slice"])
    e = meteor_event(d, meteor_track)
    print(e['meteor_lat'])
    plt.ylim([12.9, 13.1])
    plot_overpass_point(d, e['meteor_lat'], e['meteor_lon'])
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
    meteor_event(ds.sel(time=parse_segment(seg18)["slice"]), meteor_track,
                              name="Meteor overpass 1"),
    meteor_event(ds.sel(time=parse_segment(seg19)["slice"]), meteor_track,
                              name="Meteor overpass 2", remarks=["dropsonde at 2024-08-27T17:13:41"]),
    meteor_event(ds.sel(time=parse_segment(seg20)["slice"]), meteor_track,
                              name="Meteor overpass 3"),
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
