"""weedcoco.importers.deepweeds

Ingests DeepWeeds .csv annotations and images to produce a WeedCOCO .JSON file.

Modified from code from Microsoft's CameraTraps repo:
https://github.com/microsoft/CameraTraps
"""

import argparse
import pandas as pd
import pathlib
import json
import time
import datetime
from tqdm import tqdm
import humanfriendly
import os

from weedcoco.utils import get_image_dimensions

"""Constants and environment"""

# from visualization import visualize_db
# import path_utils

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--labels-dir", default=".", type=pathlib.Path)
ap.add_argument("--image-dir", default="deepweeds_images_full", type=pathlib.Path)
ap.add_argument(
    "-o", "--out-path", default="deepweeds_imageinfo.json", type=pathlib.Path
)
args = ap.parse_args()


# define paths
input_metadata_file = args.labels_dir / "labels.csv"

# filename_replacements = {dirName:'DeepWeeds'}
category_mappings = {"none": "empty"}

"""
Read source data

DeepWeeds annotations have Filename, Label, and Species columns.
"""

input_metadata = pd.read_csv(input_metadata_file)

print(
    "Read {} columns and {} rows from metadata file".format(
        len(input_metadata.columns), len(input_metadata)
    )
)


"""Main loop over labels"""

startTime = time.time()

relativePathToImage = {}

images = []
annotations = []
categoryIDToCategories = {}
missingFiles = []

duplicateImageIDs = set()

# iRow = 0; row = input_metadata.iloc[iRow]
for iRow, row in tqdm(input_metadata.iterrows(), total=len(input_metadata)):

    # ImageID,Filename,FilePath,SpeciesID
    imageID = str(row["Filename"])
    fn = row["Filename"]
    relativePath = os.path.join(args.image_dir, fn)

    # This makes an assumption of one annotation per image, which happens to be
    # true in this data set.
    if relativePath in relativePathToImage:

        im = relativePathToImage[relativePath]
        assert im["id"] == iRow
        duplicateImageIDs.add(imageID)

    else:
        im = {}
        im["id"] = iRow
        im["file_name"] = str(row["Filename"])
        im["license"] = 0
        im["agcontext_id"] = 0
        images.append(im)
        relativePathToImage[relativePath] = im

        if not os.path.isfile(relativePath):

            missingFiles.append(relativePath)

        else:
            # Retrieve image width and height
            im.update(get_image_dimensions(relativePath))

    categoryName = row["Species"].lower()
    if categoryName in category_mappings:
        categoryName = category_mappings[categoryName]

    categoryID = row["Label"]
    assert isinstance(categoryID, int)

    # Generate category objects
    if categoryID not in categoryIDToCategories:
        category = {}
        category["common_name"] = row["Species"].lower()
        category["id"] = row["Label"]
        categoryIDToCategories[categoryID] = category
        if category["common_name"] == "negative":
            category["name"] = "none"
            category["role"] = "na"
        else:
            category["role"] = "weed"
        if category["common_name"] == "chinee apple":
            category["species"] = "ziziphus mauritiana"
            category["eppo_taxon_code"] = "ZIPMA"
        if category["common_name"] == "lantana":
            category["species"] = "lantana camara"
            category["eppo_taxon_code"] = "LANCA"
        if category["common_name"] == "snake weed":
            category["species"] = "gutierrezia sarothrae"
            category["eppo_taxon_code"] = "GUESA"
        if category["common_name"] == "siam weed":
            category["species"] = "chromolaena odorata"
            category["eppo_taxon_code"] = "EUPOD"
        if category["common_name"] == "prickly acacia":
            category["species"] = "vachellia nilotica"
            category["eppo_taxon_code"] = "ACANL"
        if category["common_name"] == "parthenium":
            category["species"] = "parthenium hysterophorus"
            category["eppo_taxon_code"] = "PTNHY"
        if category["common_name"] == "rubber vine":
            category["species"] = "cryptostegia grandiflora"
            category["eppo_taxon_code"] = "CVRGR"
        if category["common_name"] == "parkinsonia":
            category["species"] = "parkinsonia aculeata"
            category["eppo_taxon_code"] = "PAKAC"
        if "name" not in category:
            category["name"] = f"{category['role']}: {category['species']}"

    # Create an annotation
    ann = {}

    # This creates a unique ID, however this feature may not be needed
    ann["id"] = iRow
    ann["image_id"] = im["id"]
    ann["category_id"] = categoryID
    ann["agcontext_name"] = "deepweeds"

    annotations.append(ann)

categories = list(categoryIDToCategories.values())

elapsed = time.time() - startTime
print(
    "Finished verifying file loop in {}, {} images, {} missing images, {} repeat labels".format(
        humanfriendly.format_timespan(elapsed),
        len(images),
        len(missingFiles),
        len(duplicateImageIDs),
    )
)
if missingFiles:
    print("Example of missing file:", missingFiles[0])

"""Create info array and object"""

info = [
    {
        "year": 2019,
        "version": 1,
        "description": "CSV annotations and JPEG images converted into WeedCOCO",
        "secondary_contributor": "Converted to WeedCOCO by Henry Lydecker",
        "contributor": "Alex Olsen",
        "id": 0,
    }
]

"""Create license array and object"""

license = [
    {
        "id": 0,
        "license_name": "CC BY 4.0",
        "license_fullname": "Creative Commons Attribution 4.0",
        "license_version": "4.0",
        "url": "https://creativecommons.org/licenses/by/4.0/",
    }
]

"""
Create collection object
"""
collections = [
    {
        "author": "Olsen, Alex",
        "title": "DeepWeeds: A Multiclass Weed Species Image Dataset for Deep Learning",
        "year": 2019,
        "identifier": "doi:10.1038/s41598-018-38343-3",
        "rights": "Apache License 2.0",
        "accrual_policy": "closed",
        "id": 0,
    }
]

# TODO: Create subset memberships from multiple csv files...
collection_memberships = [
    {"annotation_id": ann["id"], "collection_id": 0} for ann in annotations
]

"""
Create agcontext object.

A list of information necessary to provide appropriate agricultural context.
This information is invariant across a dataset upon upload.

Datasets can be concatenated to include images from multiple different agcontexts.
"""
agcontext = [
    {
        "id": 0,
        "agcontext_name": "deepweeds",
        "crop_type": "weed_only",
        "bbch_descriptive_text": "na",
        "bbch_code": "na",
        "grains_descriptive_text": "na",
        "soil_colour": "variable",
        "surface_cover": "none",
        "surface_coverage": "na",
        "weather_description": "variable",
        "location_lat": -26,
        "location_long": 150,
        "location_datum": 4326,
        "upload_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "camera_make": "FLIR Blackfly 23S6C",
        "camera_lens": "Fujinon CF25HA-1",
        "camera_lens_focallength": 25,
        "camera_height": 1000,
        "camera_angle": 90,
        "camera_fov": 28,
        "photography_description": "Mounted on tripod",
        "lighting": "natural",
        "cropped_to_plant": False,
        "url": "https://github.com/AlexOlsen/DeepWeeds",
    }
]

"""Write output"""
with args.out_path.open("w") as fout:
    json.dump(
        {
            "images": images,
            "annotations": annotations,
            "categories": categories,
            "info": info,
            "license": license,
            "agcontexts": agcontext,
            "collections": collections,
            "collection_memberships": collection_memberships,
        },
        fout,
        indent=4,
    )

print(
    "Finished writing .json file with {} images, {} annotations, and {} categories".format(
        len(images), len(annotations), len(categories)
    )
)
