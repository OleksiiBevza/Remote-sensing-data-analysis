########################################################################################
# The code assumes that the rasters are sorted in a specified folder with subfolders
# To clip the data the code:: 
#    1. loads Kosovo Boundary
#    2. walks through all raw rasters
#    3. reprojects Kosovo boundary to the raster CRS
#    4. clips the raster
#    5.  saves clipped rasters in a a folder CLIPPED DATA
# To run the script print in command prompt:
#   1. conda activate Deforestation   # activate your anaconda environment
#   2. cd "C:\Users\oleks\Desktop\DEFORESTATION\2 Logistic regression"
#   3. python "3 clip_rasters.py"
# The summary will be saved in a specified directory
#######################################################################################






# import packages
import os
import rasterio
from rasterio.mask import mask
from rasterio.errors import RasterioIOError
import geopandas as gpd


# your directory with data here
BOUNDARY_PATH = r"C:\Users\oleks\Desktop\DEFORESTATION\2 Logistic regression\0 KOSOVO BOUNDARY\gadm41_XKO_0.shp"
RAW_ROOT = r"C:\Users\oleks\Desktop\DEFORESTATION\2 Logistic regression\1 RAW DATA"
CLIPPED_ROOT = r"C:\Users\oleks\Desktop\DEFORESTATION\2 Logistic regression\2 CLIPPED DATA"

# supported formats
RASTER_EXTS = (".tif", ".tiff", ".img", ".vrt")


def main():
    """function:
            1. loads Kosovo Boundary
            2. walks through all raw rasters 
            3. reprojects Kosovo boundary to the raster CRS
            4. clips the raster
            5. saves clipped rasters in a a folder CLIPPED DATA
    """
    # load Kosovo boundary
    print("Loading Kosovo boundary shapefile...")
    kosovo = gpd.read_file(BOUNDARY_PATH)
    if kosovo.crs is None:
        raise ValueError("Kosovo boundary shapefile has no CRS defined.")

    # reprojected versions of the boundary per raster CRS
    boundary_cache = {}  # key: crs string, value: GeoDataFrame in that CRS

    # walk through the original rasters
    for dirpath, dirnames, filenames in os.walk(RAW_ROOT):
        # find rasters in given directory
        raster_files = [
            f for f in filenames
            if f.lower().endswith(RASTER_EXTS)
        ]

        # skip folders without rasters
        if not raster_files:
            continue  

        for fname in raster_files:
            in_path = os.path.join(dirpath, fname)

            # output path with same structure as original data
            rel_path = os.path.relpath(dirpath, RAW_ROOT)
            out_dir = os.path.join(CLIPPED_ROOT, rel_path)
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, fname)

            # skip if exists
            if os.path.exists(out_path):
                print(f"[SKIP] Already exists: {out_path}")
                continue

            print(f"[CLIP] {in_path}")
            try:
                # open raster
                with rasterio.open(in_path) as src:
                    if src.crs is None:
                        print(f"  Skipping (because no CRS were identified): {in_path}")
                        continue

                    # define boundary reprojected to raster CRS
                    crs_str = src.crs.to_string()
                    if crs_str not in boundary_cache:
                        boundary_cache[crs_str] = kosovo.to_crs(src.crs)
                    kosovo_proj = boundary_cache[crs_str]

                    # define geometry for clipping
                    geom = [kosovo_proj.geometry.unary_union]

                    # perform actual clipping
                    out_image, out_transform = mask(
                        src,
                        geom,
                        crop=True
                    )

                    # copy metadata and update
                    out_meta = src.meta.copy()
                    out_meta.update({
                        "height": out_image.shape[1],
                        "width": out_image.shape[2],
                        "transform": out_transform,
                    })

            except RasterioIOError as e:
                print(f"  Could not open raster: {in_path} (error: {e})")
                continue

            # save clipped raster in specified folder
            with rasterio.open(out_path, "w", **out_meta) as dst:
                dst.write(out_image)

            print(f"  Saved clipped raster to: {out_path}")

    print("\nDone! All rasters clipped to Kosovo are under:")
    print(CLIPPED_ROOT)


if __name__ == "__main__":
    main()
