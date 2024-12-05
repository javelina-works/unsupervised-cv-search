import matplotlib.pyplot as plt
# import rasterio
import cv2
import os

# Load an image (GeoTIFF or standard formats)
def load_image(file_path):
    try:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
        # if file_path.endswith('.tif'):
        #     # Use rasterio for GeoTIFFs
        #     with rasterio.open(file_path) as src:
        #         image = src.read([b for b in range(1, src.count + 1)]).transpose(1, 2, 0)  # RGB(A)
        #         return image
        else:
            # Use OpenCV or PIL for standard formats
            return cv2.cvtColor(cv2.imread(file_path), cv2.COLOR_BGR2RGB)
    except Exception as e:
        print(f"Error loading image: {e}")
        return None

# Visualize the image
def plot_image(image, title="Image"):
    plt.figure(figsize=(10, 8))
    plt.imshow(image)
    plt.title(title)
    plt.axis('off')
    plt.show()
