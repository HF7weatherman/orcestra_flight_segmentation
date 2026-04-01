import xarray as xr

def get_pace_track(t_start, t_end):
    return xr.open_dataset(
        "ipfs://QmfMH7HJveBJsHERphikd2QnswE2bTtyZo12tap5vbfsvS",
        engine="zarr",
    ).sel(time=slice(t_start, t_end))

def main():
    from datetime import datetime, UTC
    import logging

    logging.basicConfig(level=logging.DEBUG)
    print(get_pace_track(datetime(2024,9,20, tzinfo=UTC), datetime(2024,9,20,1, tzinfo=UTC)))

if __name__ == "__main__":
    exit(main())
