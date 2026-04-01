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

# Flight segmentation HALO-20240923a

```python
import matplotlib
import yaml
import hvplot.xarray
import xarray as xr
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from orcestra import bco
from navdata import get_navdata_HALO
from utils import *
```

```python
platform = "HALO"
flight_id = "HALO-20240923a"
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
print("take-off: ", takeoff)
print("landing: ", landing)
print(f"flight duration (hh:mm): {int(duration / 60)}:{int(duration % 60)}")
```

### Get EC track and EC meeting point

```python
_ec_track = get_ec_track(flight_id, ds)
ec_track = _ec_track.where(
        (_ec_track.lat > ds.lat.min()-2) & (_ec_track.lat < ds.lat.max()+2) &
        (_ec_track.lon > ds.lon.min()-2) & (_ec_track.lon < ds.lon.max()+2),
        drop=True)
dist_ec, t_ec = get_overpass_track(ds, ec_track)
```

### Get PACE track

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
if meteor_track: plt.plot(meteor_track.lon, meteor_track.lat, c="C4", ls="-", label="METEOR track", zorder=20)
plt.ylim([8, 15])
plt.xlabel("longitude / °")
plt.ylabel("latitude / °")
plt.legend()

#test display of foto location
fotos = [
    "2023-09-23T11:23:58",
    "2023-09-23T11:34:10",
    "2023-09-23T12:00:10",
    ]
foto = False
if foto:
    for i in fotos:
        da_foto = ds.sel(time=i, method="nearest")
        plt.scatter(da_foto.lon, da_foto.lat, color='C1', marker='o', s = 10, zorder=100)
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
# segment at roughly 930m altitude, but with two different roll angles -> maybe name it just "leg" and specify irreg?
seg1 = (slice("2024-09-23T11:17:49", "2024-09-23T11:18:39"),
        ["straight_leg", "meteor_coordination"],
        "ferry_towards_meteor",
        ["segment at roughly 930m altitude",
         "including first METEOR overpass and BCO bypass"],
       )

# climbing circle (with Meteor overpass)
seg2 = (slice("2024-09-23T11:21:42", "2024-09-23T11:54:32"),
        ["ascent", "circle", "circle_clockwise", "meteor_coordination"],
        "circle_ascent",
        ["circle to climb up to FL410", "including 2nd METEOR overpass"],
       )

# Meteor measurement circle (with Meteor overpass) on FL410
seg3 = (slice("2024-09-23T11:54:32", "2024-09-23T12:26:35"),
        ["circle", "meteor_coordination", "circle_clockwise", "meteor_coordination"],
        "circle_meteor",
        ["irregularity: roll angle deviations up to +-6 degree from segment start until 11:56:20 due to deep convection",
         "including 3rd METEOR overpass",
        ],
       )

# heading to c_mid
seg4a = (slice("2024-09-23T12:31:33", "2024-09-23T12:40:20"),
        ["straight_leg"],
        "ferry_eastward_towards_circle_mid_1",
        [],
       )

seg4b = (slice("2024-09-23T12:40:20", "2024-09-23T12:44:10"),
        ["straight_leg", "ascent"],
        "ferry_eastward_ascent_to_fl430",
        [],
       )

seg4c = (slice("2024-09-23T12:44:10", "2024-09-23T13:08:51"),
        ["straight_leg"],
        "ferry_eastward_towards_circle_mid_2",
        [],
       )

seg6 = (slice("2024-09-23T13:12:20", "2024-09-23T14:07:30"),
        ["circle", "circle_clockwise"],
        "circle_mid",
        ["irregularity: deviation from circular path due to deep convection with roll angle deviations up to +-28 degree between 13:21:57 - 13:31:10"],
       )

seg7 = (slice("2024-09-23T14:11:01", "2024-09-23T14:26:28"),
        ["straight_leg"],
        "ferry_eastward_through_circle_mid",
        ["irregularity: spike with roll angle deviation of -3 degree"],
       )

seg8 = (slice("2024-09-23T14:26:28", "2024-09-23T14:31:32"),
        ["straight_leg", "ascent"],
        "ferry_eastward_ascent_to_fl450",
        [],
       )
       
# fl change 14:26:29 - 14:31:29 and again 14:35:43 - 14:37:34
# straight_leg and circle start still with FL change

seg9 = (slice("2024-09-23T14:37:34", "2024-09-23T15:32:20"),
        ["circle", "circle_clockwise"],
        "circle_around_ec_track",
        ["irregularitiy: late start due to FL change, on circle roughly since 14:32:30",
        "irregularity: deviation from circular path due to deep convection with roll angle deviations up to +- 16 degree"]
       )

seg10 = (slice("2024-09-23T15:36:28", "2024-09-23T15:57:14"),
         ["straight_leg"],
         "ferry_eastward_through_circle_around_ec_track",
         ["irregularity: spike in rool angle up to -5.65deg between 15:42:23-15:42:36"],
        )

seg11 = (slice("2024-09-23T16:00:47", "2024-09-23T16:55:23"),
         ["circle", "circle_counterclockwise"],
         "circle_south",
         ["irregularity: deviation from circular path due to deep convection in southern half, 16:15:30 - 16:18:30, with roll angle deviations up to +-30 degree.",
         "irregularity: deviation from circular path due to deep convection in northern half, from 16:47:06 until the segment ends, with roll angle deviations up to +-28 degree."],
        )

seg12 = (slice("2024-09-23T16:57:01", "2024-09-23T17:12:15"),
         ["straight_leg"],
         "ferry_towards_ec_track_at_ec_south",
         ["irregularity: roll angle spike up to 5.1 degree"],
        )

seg13 = (slice("2024-09-23T17:15:25", "2024-09-23T17:23:46"),
         ["straight_leg", "ec_track"],
         "ec_track_northward",
         ["irregularity: the EC track is very short due to very deep convection in the south and north but covers the meeting point"],
        )

# heavy deviations to navigate through deep concevtion towards next circle
#seg14 = (slice("2024-09-23T17:23:47", "2024-09-23T17:54:38"),)

seg14 = (slice("2024-09-23T17:54:38", "2024-09-23T17:57:27"),
        ["straight_leg"],
        "ferry_towards_circle_west_1",
        [],
        )

seg15 = (slice("2024-09-23T17:57:27", "2024-09-23T18:03:16"),
        ["straight_leg", "ascent"],
        "ferry_towards_circle_west_ascent_to_fl470",
        [],
        )

seg16 = (slice("2024-09-23T18:03:17", "2024-09-23T18:12:36"),
        ["straight_leg"],
        "ferry_towards_circle_west_2",
        [],
        )

seg17 = (slice("2024-09-23T18:15:51", "2024-09-23T19:10:36"),
        ["circle", "circle_clockwise"],
        "circle_west",
        [],
        )

seg18 = (slice("2024-09-23T19:12:57", "2024-09-23T19:16:45"),
        ["straight_leg"],
         "straight_leg_through_circle_west",
         [],
        )

seg19 = (slice("2024-09-23T19:16:59", "2024-09-23T19:18:43"),
        ["radar_calibration_wiggle"],
        "radar_calibration_wiggle_within_circle_west",
         ["pattern within circle west with 12 sondes"],
        )

# straight leg crossing c_west
seg20 = (slice("2024-09-23T19:21:24", "2024-09-23T19:26:39"),
        ["straight_leg"],
        "ferry_westward_through_circle_west",
        [],
        )

# FL change down to ~2km consisting of 3 straight legs
#seg21 = (slice("2024-09-23T19:26:40", "2024-09-23T19:46:55"),)
# FL change leg 1
seg21a = (slice("2024-09-23T19:26:40", "2024-09-23T19:32:04"),
         ["straight_leg", "descent"],
          "ferry_westward_towards_meteor_descent_1",
          [],
         )

# FL change leg 2
seg21b = (slice("2024-09-23T19:34:08", "2024-09-23T19:41:36"),
          ["straight_leg", "descent"],
          "ferry_westward_towards_meteor_descent_2",
          [],
         )

# FL change leg 3
seg21c = (slice("2024-09-23T19:42:37", "2024-09-23T19:46:56"),
          ["straight_leg", "descent"],
          "ferry_westward_towards_meteor_descent_3",
          [],
         )

# straight leg overpassing Meteor at 2km height
seg22 = (slice("2024-09-23T19:46:56", "2024-09-23T19:53:45"),
         ["straight_leg", "meteor_coordination"],
         "straight_leg_overpassing_meteor_at_2km_altitude",
         ["only BAHAMAS instrument still running",
         "irregularity: roll angle deviations up to +-6.7 degree"],
        )
# again FL change
#seg23 = (slice("2024-09-23T19:53:44", "2024-09-23T19:56:41"),)

# straight_leg passing by BCO at ~900m height at 19:56:57
seg24 = (slice("2024-09-23T19:56:50", "2024-09-23T19:58:11"),
        ["straight_leg"],
         "straight_leg_overpassing_bco_at_900m_altitude",
         ["only BAHAMAS instrument still running"],
        )

# landing
#seg25 = (slice("2024-09-23T19:58:12", "2024-09-23T20:09:49"),)
```

### adding all segments to a list that shall be further evaluated and saved to YAML

```python
segments = [parse_segment(s) for s in [seg1, seg2, seg3, seg4a, seg4b,
                                       seg4c, seg6, seg7, seg8, seg9,
                                       seg10, seg11, seg12, seg13, seg14,
                                       seg15, seg16, seg17, seg18, seg19,
                                       seg20, seg21a, seg21b, seg21c, seg22,
                                       seg24]
           ]
```

### Quick plot for working your way through the segments piece by piece
select the segment that you'd like to plot and optionally set the flag True for plotting the previous segment in your above specified list as well. The latter can be useful for the context if you have segments that are close or overlap in space, e.g. a leg crossing a circle.

```python
seg=parse_segment(seg3)
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

### Meteor and BCO coordination
How far was the Meteor/BCO away from the HALO track?
Overpasses happened within the first three segments and before landing.


#### Plot Meteor overpasses

```python
for s in [seg1, seg2, seg3, seg22]:
    d = ds.sel(time=parse_segment(s)["slice"])
    e = meteor_event(d, meteor_track)
    plot_overpass_point(d, e['meteor_lat'], e['meteor_lon'])
```

#### Plot BCO overpasses
Use the high resolution BAHAMAS data here to get the most accurate info on closest point and time.

```python
ds_hres = get_navdata_HALO(flight_id, hres=True)

for s in [seg1, seg24]:
    plot_overpass_point(ds_hres.sel(time=parse_segment(s)["slice"]), bco.lat, bco.lon)
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
events = [target_event(ds_hres.sel(time=parse_segment(seg1)["slice"]), target="BCO",
                      name="passing by BCO"),
          meteor_event(ds.sel(time=parse_segment(seg1)["slice"]), meteor_track,
                       name="Meteor overpass 1"),
          meteor_event(ds.sel(time=parse_segment(seg2)["slice"]), meteor_track,
                       name="Meteor overpass 2"),
          meteor_event(ds.sel(time=parse_segment(seg3)["slice"]), meteor_track,
                       name="Meteor overpass 3"),
          ec_event(ds, ec_track,
                   ec_remarks=["sharp turn away from EC track right after meeting point due to deep convection"]),
          meteor_event(ds.sel(time=parse_segment(seg22)["slice"]), meteor_track,
                       name="Meteor overpass 4"),
          target_event(ds_hres.sel(time=parse_segment(seg24)["slice"]), target="BCO",
                      name="BCO overpass 2"),
         ]
events
```

## Parse info to YAML file

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

for k, c in zip(['straight_leg', 'circle', 'radar_calibration'], ["C0", "C1", "C2"]):
    for s in flight["segments"]:
        if k in s["kinds"]:
            t = slice(s["start"], s["end"])
            ax.plot(ds.lon.sel(time=t), ds.lat.sel(time=t), c=c, label=s["name"])
ax.set_xlabel("longitude / °")
ax.set_ylabel("latitude / °");
```
