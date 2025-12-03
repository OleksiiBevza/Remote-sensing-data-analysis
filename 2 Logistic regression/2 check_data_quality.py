########################################################################################
# The code assumes that the rasters are sorted in a specified folder with subfolders
# To check the data quality the code: 
#    1. extracts its CRS (coordinate reference system)
#    2. extracts its resolution (pixel width/height)
#    3. writes and saves a report with summary
# To run the script print in command prompt:
#   1. conda activate Deforestation   # activate your anaconda environment
#   2. cd "C:\Users\oleks\Desktop\DEFORESTATION\2 Logistic regression"
#   3. python "2 check_data_quality.py"
# The summary will be saved in a specified directory
#######################################################################################





# import packages
import os
import rasterio
from rasterio.errors import RasterioIOError


# dirctory with data
ROOT_DIR = r"C:\Users\oleks\Desktop\DEFORESTATION\2 Logistic regression\1 RAW DATA"
# look for possible rasters format
RASTER_EXTS = (".tif", ".tiff", ".img", ".vrt")
# save summary
REPORT_PATH = os.path.join(os.getcwd(), "raster_report.txt")



def classify_resolution_meters(val_m):
    """function returns a string for a cell size in meters"""
    v = abs(val_m)
    # resolutions are close to
    if abs(v - 30) < 5:
        return "30 m"
    if abs(v - 100) < 20:
        return "100 m"
    if abs(v - 250) < 50:
        return "250 m"
    if abs(v - 500) < 80:
        return "500 m"
    if abs(v - 1000) < 200:
        return "1 km"
    if abs(v - 5000) < 500:
        return "5 km"
    if abs(v - 10000) < 1000:
        return "10 km"

    # return results
    if v < 1000:
        return f"{v:.1f} m"
    else:
        return f"{v/1000:.2f} km"



def pretty_resolution(res, folder_crs):
    """
    function checkes whether resolution units are meters or degrees
    converts degrees to meters if needed
    return a string with spatial resolution in meters or kilometers
    """
    xres, yres = res

    # if CRS unknown, return raw numbers
    if folder_crs is None:
        return f"{xres} x {yres} (units of CRS)"

    # if projected CRS: treat resolution as meters:
    if folder_crs.is_projected:
        x_m = xres
        y_m = yres

    # if geographic CRS (EPSG:4326 or else): 
    # then units are degrees so approximate metres
    elif folder_crs.is_geographic:
        # approximation: 1 degree ~ 111.32 km
        km_per_deg = 111.32
        x_m = xres * km_per_deg * 1000
        y_m = yres * km_per_deg * 1000
    else:
        # return unknown unit type
        return f"{xres} x {yres} (units of CRS)"

    x_str = classify_resolution_meters(x_m)
    y_str = classify_resolution_meters(y_m)
    return f"{x_str} x {y_str}"



def inspect_rasters(root_dir, report_path):
    """functions walks though the data folder entering every subfolder
       looking for a rasters. When found: 
            1) extracts its CRS (coordinate reference system)
            2) extracts its resolution (pixel width/height)
            3) writes and saves a report with summary
    """
    log_lines = []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # find raster files in given directory
        raster_files = [
            f for f in filenames
            if f.lower().endswith(RASTER_EXTS)
        ]

        if not raster_files:
            continue  # skip folders without rasters

        crs_info = []       # list of (filename, crs)
        res_info = []       # list of (filename, (xres, yres))
        missing_crs = []    # rasters with no CRS
        failed_files = []   # rasters that were not opened
        folder_crs_obj = None  # store one CRS object for this folder

        for fname in raster_files:
            fpath = os.path.join(dirpath, fname)
            try:
                with rasterio.open(fpath) as src:
                    # read CRS and pixel resolution
                    crs = src.crs
                    res = src.res  # (pixel_width, pixel_height)
                    # add them to the lists
                    crs_info.append((fname, crs))
                    res_info.append((fname, res))

                    # if no CRS append to other list
                    if crs is None:
                        missing_crs.append(fname)
                    else:
                        # save one CRS object 
                        if folder_crs_obj is None:
                            folder_crs_obj = crs

            # if failed append to another list
            except RasterioIOError as e:
                failed_files.append((fname, str(e)))

        # build sets of CRS and resolutions present in this folder
        crs_groups = {}
        for fname, crs in crs_info:
            if crs is None:
                continue
            crs_str = crs.to_string()  # like 'EPSG:32634'
            crs_groups.setdefault(crs_str, []).append(fname)

        res_groups = {}
        for fname, res in res_info:
            res_groups.setdefault(res, []).append(fname)

        # -----------------------------------------------
        # Build summary for a current folder 
        # -----------------------------------------------
        log_lines.append("=" * 100)
        log_lines.append(f"Folder: {dirpath}")
        log_lines.append(f"  Rasters found: {len(raster_files)}")
        log_lines.append(f"  Successfully opened: {len(crs_info)}")
        if failed_files:
            log_lines.append("  Could not open these rasters:")
            for fname, msg in failed_files:
                log_lines.append(f"    - {fname} (error: {msg})")

        # CRS check
        if missing_crs:
            log_lines.append("\n  Rasters WITHOUT CRS defined:")
            for fname in missing_crs:
                log_lines.append(f"    - {fname}")
        else:
            log_lines.append("\n  All rasters have a CRS defined.")

        if crs_groups:
            if len(crs_groups) == 1 and not missing_crs:
                crs_str = next(iter(crs_groups.keys()))
                log_lines.append(f"  All rasters share the same CRS: {crs_str}")
            else:
                log_lines.append(f"  Multiple CRS detected ({len(crs_groups)}):")
                for crs_str, files in crs_groups.items():
                    log_lines.append(f"    CRS: {crs_str}")
                    for fname in files:
                        log_lines.append(f"      - {fname}")
        else:
            log_lines.append("  No CRS information could be read from any raster in this folder.")

        # resolution check
        if res_groups:
            if len(res_groups) == 1:
                res = next(iter(res_groups.keys()))
                pretty_res = pretty_resolution(res, folder_crs_obj)
                log_lines.append(f"\n  All rasters share the same resolution: {pretty_res}")
            else:
                log_lines.append("\n  Multiple resolutions detected:")
                for res, files in res_groups.items():
                    pretty_res = pretty_resolution(res, folder_crs_obj)
                    log_lines.append(f"    Resolution {pretty_res}:")
                    for fname in files:
                        log_lines.append(f"      - {fname}")
        else:
            log_lines.append("\n  No resolution information found.")

        # summary if everything is consistent
        if (not missing_crs
            and len(crs_groups) == 1
            and len(res_groups) == 1):
            res = next(iter(res_groups.keys()))
            pretty_res = pretty_resolution(res, folder_crs_obj)
            log_lines.append(
                f"\n  Summary: all rasters in this folder have a CRS"
                # f"resolution {pretty_res}."
            )

        log_lines.append("")  # blank line between folders

    # write report as txt
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))


if __name__ == "__main__":
    inspect_rasters(ROOT_DIR, REPORT_PATH)
    print(f"Report saved to: {REPORT_PATH}")