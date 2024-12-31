from plant_search.vegetation_indices import calculate_exg, normalize_rgb
from skimage.exposure import equalize_adapthist
from skimage.morphology import opening, closing, disk
from skimage.filters import threshold_otsu
from skimage.measure import label, regionprops
import cv2
import numpy as np



def generate_target_mask(image):

    # Normalize ExG to the range [0, 255] for OpenCV compatibility
    exg = calculate_exg(*normalize_rgb(image))
    exg_normalized = (exg - np.min(exg)) / (np.max(exg) - np.min(exg))  # Normalize to [0, 1]
    exg_uint8 = (exg_normalized * 255).astype(np.uint8)


    # Step 1: Bilateral Filtering using OpenCV
    bl_sigma_color = 50
    bl_sigma_spatial = 15 # Lower number is faster

    bilateral_smoothed_exg = cv2.bilateralFilter(
        exg_uint8 , d=9, 
        sigmaColor=bl_sigma_color, 
        sigmaSpace=bl_sigma_spatial
    )
    bilateral_smoothed_exg = bilateral_smoothed_exg / 255.0  # Scale back to [0, 1]

    # Step 2: Contrast Enhancement with CLAHE
    clahe_exg = equalize_adapthist(bilateral_smoothed_exg, clip_limit=0.008)

    # Step 3: Morphological Operations (Opening → Closing)
    selem = disk(7)  # Structuring element
    morph_exg = closing(opening(clahe_exg, selem), selem)

    # Step 4: Thresholding (Otsu's method)
    otsu_threshold = threshold_otsu(morph_exg)
    binary_mask = morph_exg > otsu_threshold

    return binary_mask


def identify_targets(binary_mask):
    # Step 1: Preprocess the binary mask
    selem = disk(3)  # Structuring element
    cleaned_mask = closing(binary_mask, selem)  # Fill small gaps

    # Step 2: Label connected components
    labeled_mask = label(cleaned_mask)
    regions = regionprops(labeled_mask)

    # Step 3: Extract centroids and bounding boxes
    centroids = []
    bounding_boxes = []

    for region in regions:
        # Centroid
        centroid = region.centroid  # (row, col)
        centroids.append((round(centroid[1], 2), round(centroid[0], 2)))  # Format x, y to 2 decimal places

        # Bounding box
        min_row, min_col, max_row, max_col = region.bbox
        bounding_boxes.append(((min_col, min_row), (max_col, max_row)))

    return centroids, bounding_boxes