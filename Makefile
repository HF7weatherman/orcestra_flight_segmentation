HALO_FLIGHTS = $(patsubst scripts/segmentation_%.md,%,$(wildcard scripts/segmentation_HALO*.md))
HALO_SEGMENT_FILES = $(patsubst %, flight_segment_files/%.yaml, ${HALO_FLIGHTS})
HALO_REPORTS = $(patsubst %, reports/%.html, ${HALO_FLIGHTS})
ATR_SEGMENT_FILES = $(wildcard flight_segment_files/as24*.yaml)

all: reports/all_flights.yaml ${HALO_REPORTS} reports/index.html

.PHONY: all

reports/all_flights.yaml: ${HALO_SEGMENT_FILES} ${ATR_SEGMENT_FILES}
	mkdir -p reports
	python3 scripts/merge_segments.py -o $@ -i $^

flight_segment_files/HALO%.yaml: scripts/segmentation_HALO%.md
	mkdir -p flight_segment_files
	jupytext --use-source-timestamp --execute $<

reports/%.html: flight_segment_files/%.yaml scripts/report.py scripts/templates/flight.html
	mkdir -p reports
	python3 scripts/report.py $< $@

reports/index.html: reports/all_flights.yaml Makefile scripts/index.py scripts/templates/index.html
	mkdir -p reports
	python3 scripts/index.py -o $@ -s $<
