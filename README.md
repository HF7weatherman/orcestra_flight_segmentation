# Segmentation of HALO research flights

**TL;DR: The HALO flight segmentation is available at [all_flights.yaml](https://orcestra-campaign.github.io/flight_segmentation/all_flights.yaml) and from the [orcestra python package](https://github.com/orcestra-campaign/pyorcestra).**


The research flights during ORCESTRA can be divided into segments which are specific time intervals during a flight with coherent characteristics. 
The coherent characteristics, referred to as "kinds", typically refer to the aircraft's state during a flight maneuver as read out from the aircraft position and flight attitude data, such as a roughly constant heading, altitude, and roll angle on a `straight_leg`, or a fairly circular flight path on a `circle`. 
Further, kinds may indicate colocated measurements with the EarthCARE (EC) satellite (`ec_track`) or other campaign platforms such as the ATR aircraft (`atr_coordination`).
Apart from time *intervals* referred to as `segments`, the flight segmentation also contains *single points in time* referred to as `events` which also get specified by kinds and mark, for instance, the time at which the aircraft was closest in space and time to the EC satellite (`ec_underpass`), the Meteor research vessel (`meteor_overpass`), or ground measurement stations such as the CVAO in Mindelo (`cvao_overpass`) or the BCO on Barbados (`bco_overpass`).

The goal of the flight segmentation is to provide a commonly agreed upon, consistent, and easy-to-use subsampling functionality that can be used by reserachers who work with the ORCESTRA measurement data. 
For instance, studies concerned with the EarthCARE validation can select all segments of kind `ec_track` to obtain all time intervals in which HALO was flying on the EarthCARE track.
Similarly, all studies that analyse data taken on circular flight paths can use the flight segmentation to select segments of kind `circle`, and are thereby guaranteed to refer to the same commonly agreed upon subset of the campaign data. 
The `events` further enable the selection of colocated measurements that can directly be compared with each other.

## Finding the file and working with it
The segments of all reasearch flights are specified and stored in a yaml-file called [all_flights.yaml](https://orcestra-campaign.github.io/flight_segmentation/all_flights.yaml) which gets its input from segmentation notebooks for all individual flights. 
Note that these executable notebooks are saved as markdown files to facilitate a reasonable git workflow and track changes. 
These segmentation files are stored in [flight_segmentation/scripts](https://github.com/orcestra-campaign/flight_segmentation/tree/main/scripts) and act as the single point of truth for the definition of segments. 
The Github workflows defined in the current repository execute all segmentation files and create and publish the `all_flights.yaml` upon each commit to this repository. Collaborators are encouraged to add or modify segments and events as they see fit.

A tutorial with practical examples for how to import and use the flight segmentation for data analyses with python are provided on the [ORCESTRA campaign website](https://orcestra-campaign.org/halo_flight_segmentation.html).


## Structure of the all_flights.yaml file
The following excerpt from the all_flights.yaml file, further explained below, demonstrates the structure of the flight segmentation:

```yaml
HALO:
  HALO-20240811a:
    mission: ORCESTRA
    platform: HALO
    flight_id: HALO-20240811a
    takeoff: 2024-08-11 11:59:34
    landing: 2024-08-11 20:35:56
    events:
      - event_id: HALO-20240811a_243c
        name: EC meeting point
        time: 2024-08-11 15:51:53.745187
        kinds:
          - ec_underpass
        remarks: []
        distance: 1123
    segments:
      - segment_id: HALO-20240811a_7051
        name: EC_track_southward_const_alt
        start: 2024-08-11 12:29:59
        end: 2024-08-11 14:03:40
        kinds:
          - straight_leg
          - ec_track
        remarks:
          - 'irregularity: turbulence 2024-08-11T13:02:15 - 2024-08-11T13:12:00'
      - segment_id: HALO-20240811a_50ca
        name: circle_south
        start: 2024-08-11 14:17:00
        end: 2024-08-11 15:16:17
        kinds:
          - circle
        remarks: []
        clat: 5.000066183128026
        clon: -26.999928980187303
        radius: 133094.75108481143
```

We make use of a typical YAML block style for structuring the segmentation data. 
In order to allow other sub-campaigns to add their flight/ship track segmentation, the file begins with a general block stating the campaign platform (HALO, ATR, METEOR,...). 
The second level is formed by blocks containing the segmentation information for individual research flights denoted by their `flight_id` (e.g. HALO-20240811a). 
Each flight-block includes a mapping of the following attributes: `mission` affiliation (ORCESTRA), `platform`, `flight_id`, `takeoff` and `landing` time, `events`, and `segments`. 
The two attributes `events`and `segements` are special in the sense that they each include a list of respective events or flight segments from the corresponding research flight. 
Times are generally provided in format `YYYY-MM-DD HH:MM:SS`.

#### Events
The `events` attribute lists all the single points in time when underpasses and overpasses occurred. 
An event is specified by a *unique* `event_id`, constructed from the `flight_id` and a hash computed from the event `time`, a `name` (a short qualitative description), a `time`, and the event `kinds` (e.g. ec_underpass). 
The attribute `remarks` may contain custom comments about irregularities or other noteworthy information. 
Last, the `distance` between HALO and the other platform (e.g. EarthCARE satellite), as projected on the Earth's surface, is provided in meters. 
In case of an event that describes a meeting point with another moving platform, e.g. the Meteor ship, the coordinates in the form of latitude and longitude of that second moving platform are stated, too. 
For instance, in the case of a `meteor_overpass`, the key/value pairs for `meteor_lat`and `meteor_lon` would be added to the event.

#### Segments
After the event listing, `segments` lists all identified flight segments which follow a similar structure as `events` with a *unique* `segment_id`, a `name`, a specification of the time interval by a `start` and `end` time (which both enter the computation of the hash used for `segment_id`), `kinds`, and `remarks`. 
Note that the time ranges, constructed from `start` and `end` are defined as semi-open intervals, i.e. while the start time is inside the segment, the end time is not. 
This allows for an unambiguous definition of exactly consecutive segments. 
For segments of kind `circle`, the latitude `clat` and longitude `clon` of the circle center, as well as the circle `radius` in meters are added as additional attributes. 
As for events, the `remarks` attribute lists free text comments, including irregularities such as deviations from the envisioned flight track due to deep convection or roll angle spikes due to turbulence which one may want to exclude from scientific analysis. 
To enable automated checking, such irregularity remarks start with "irregularity:".

While `event_id`, `segment_id`, as well as `time`, `start`, and `end` are mandatory attributes for events and segments, all other attributes are optional. 
Nevertheless, providing the `kinds` attribute, which can be thought of as tags, is highly recommended because it constitutes the primary filtering criterion. 
A list of all tags currently in use is provided below.


## Definition of kinds
Kinds may or may not apply/be adopted for all platforms. 
For the first version of the segmentation of HALO research flights, one or more of the following kinds are assigned to each segment or event:

| kind | used for | description
| --------| ------- | ------- |
| ascent       | segments | assigned to straight legs or circles during which the aircraft altitude was increased systematically by more than a few meters, typically to a new [flight level](https://en.wikipedia.org/wiki/Flight_level). |
| atr_coordination | segments | assigned to segments, typically circles, during which HALO took measurements colocated in space and time with the ATR aircraft (however, not necessarily with a direct overpass of the two aircrafts); in some cases, the measurements were only colocated in space. |
| bco_overpass | events | assigned to events where the aircraft flew roughly over the [Barbados Cloud Observatory](https://barbados.mpimet.mpg.de/). |
| c_pirouette  | segments | assigned to circles that were flown around an individual cloud object |
| circle       | segments | roughly circular flight pattern, identified by a fairly constant change of aircraft heading at fairly constant roll angles between ±(1.5 to 5)&deg;, depending on the circle radius; HALO flew two typical circle configurations: a standard circle with a radius of about 133km and a duration of about one hour, and a smaller circle with a radius of about 70km and a duration of about 40min, typically flown in coordination with ATR measurements (`atr_coordination`); most circles were associated with the launch of dropsondes, typically 12 per circle at every 30&deg; heading; in cases where the first (last) dropsonde of the circle was launched before (after) roll angle and change in heading match the circle characteristics described above, the start (end) time of the circle segment is taken to be the `launch_time` of the respective dropsonde minus (plus) 1 second; some circles were highly irregular due to deviations around deep convection in which case this is mentioned in an irregularity `remark`.|
| circle_clockwise | segments | assigned to `circles` that were flown in clockwise direction (i. e. with a positive roll angle) |
| circle_counterclockwise | segments | assigned to `circles` that were flown in counterclockwise direction (i. e. with negative roll angle) |
| cvao_overpass | events | assigned to events where the aircraft flew roughly over the Cape Verde Atmospheric Observatory in Mindelo|
| descent      | segments | assigned to straight legs or circles during which the aircraft altitude was decreased systematically by more than a few meters |
| ec_track     | segments | assigned to straight legs during which the aircraft followed the EarthCare track. Aircraft and EarthCare flight direction can be the same or opposite. |
| ec_underpass | events | assigned to events where the aircraft flew as close as possible under the EarthCARE satellite |
| meteor_coordination | segments | assigned to segments during which HALO flew around or in the vicinity of the Meteor research vessel; note that in the case of long segments, this characterization may only be apt for a smaller time interval within the segment in which case further subsampling may be done by checking for an `meteor_overpass` event. |
| meteor_overpass | events | assigned to events where the aircraft flew roughly over the Meteor research vessel |
| mim_overpass | events | assigned to events where the aircraft flew roughly over the Meteorological Institute in Munich |
| pace_track | segments | assigned to straight legs during which the aircraft followed the PACE track; note that measurements taken in other segments may also be colocated with PACE due to the satellite's wide swath. |
| pace_underpass | events | assigned to events where the aircraft flew as close as possible under the PACE satellite. |
| radar_calibration_dive | segments | three consecutive stepwise descents with a total altitude decrease of about 1km within about 2.5min, performed during a descending straight leg |
| radar_calibration_wiggle | segments | flight maneuver typically conducted on a straight leg, where the aircraft's roll angle is alternated (typically) 2 times ±20&deg; with 1&deg; per second; the segment starts and ends at about 0&deg; roll angle.|
| smart_calibration | segments | flight maneuver during which the aircraft takes four consecutive turns with about 25&deg roll angle; the maneuver is used to calibrate the SMART-HALO upper irradiance sensors and position stabilization |
| straight_leg | segments | flight pattern with approximately constant heading and a roll angle close to 0&deg;; outstanding short-term roll angle deviations (approximately beyond ±2&deg;) due to turbulence are mentioned as irregularities in the remarks attribute|

<!-- #region -->
## HALO segmentation workflow for developers

The flight segmentation workflow broadly consists of three phases:
1. Segmentation of a flight
2. Review of the segmentation in pairs (the person who performed the segmentation + one other colleague)
3. Handover of the final flight segmentation (along with suggestions for how to improve the flight report where necessary) to the corresponding flight-PI for cross-checking.


How to contribute to the flight segmentation:

1. Fork the flight segmentation repository and clone it to get your local copy.
2. Install the requirements noted [here](environment.yaml) as well as the [IPFS Desktop App](https://docs.ipfs.tech/install/ipfs-desktop/), e.g. on Mac via `brew install --cask ipfs`.
3. Build a respective python environment, e.g. `mamba env create -f environment.yaml`
4. Assign yourself to an existing open segmentation issue of this repository or a new one that you created for your development goal.
5. Make a change to an existing segmentation file in `scripts` by opening it as an ipython notebook, or create a new segmentation file by making a copy of the file `scripts/segmentation_template.md`, renaming it accordingly. 
In the case of a new file, load the BAHAMAS and dropsonde data to determine the individual segments, using a mix of bokeh and other plots of roll angle, altitude, heading or other measures. The corresponding [flight report](https://github.com/orcestra-campaign/book/tree/main/orcestra_book/reports) aids the identification of irregularities and rare flight maneuvers such as instrument calibrations.
7. Test the build of the `all_flight.yaml` by executing `make -j` in the top level folder of your cloned repository.
9. Add your final notebook file to the repository by creating a pull request and assigning a reviewer.
10. Review your segmentation together with one other colleague. 
You can use the automated HTML reports generated by the Makefile. 
Locally they are available at `/reports/*.html` after executing `make -j`.
When a PR is merged, the GitHub workflows generate and publish all files from the `/reports` folder at https://orcestra-campaign.github.io/flight_segmentation/.
11. Check for inconsistencies with the [flight report](https://github.com/orcestra-campaign/book/tree/main/orcestra_book/reports) and send corresponding suggestions for improvement, together with your reviewed flight segmentation to the respective flight-PI for final feedback.
<!-- #endregion -->

## Further information

#### YAML files
The flight segmentation data is provided in YAML files. 
YAML is a text based, human readable data format that uses python-like indentation for structuring its contents. 
It is often used for configuration files and due to its great human readability very suited for version control, which is one reason we wanted to use it here.
For python users, the module [PyYAML](https://pyyaml.org) (included in Anaconda) offers an easy to use way to read the data from the yaml files into plane python objects like lists and dictionaries.
Here is an example to read a file and print the circle start and end times from that file:

```
import yaml
flightinfo = yaml.load(open("HALO_20240813a.yaml"))
print([(c["start"], c["end"]) for c in flightinfo["segments"] if "circle" in c["kinds"]])
```

#### Legacy
The segmentation copies and adapts many ideas from the [flight segmentation](https://github.com/eurec4a/flight-phase-separation) conducted for the EUREC4A field campaign.

