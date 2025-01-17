import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from rio_tiler.io import COGReader
from rio_tiler.errors import TileOutsideBounds
from PIL import Image
import numpy as np
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Path to your GeoTIFF
GEOTIFF_PATH = 'outputs/reprojected_region.tif'


def generate_tiles(geo_tiff_path, output_dir, zoom_levels):
    """Generate tiles for a GeoTIFF."""
    from mercantile import tiles, bounds
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with COGReader(geo_tiff_path) as cog:
        geo_bounds = cog.bounds
        for z in zoom_levels:
            for tile in tiles(*geo_bounds, z):
                try:
                    tile_data, mask = cog.tile(tile.x, tile.y, z)
                    rgba = np.dstack((tile_data[0], tile_data[1], tile_data[2], mask)).astype(np.uint8)
                    img = Image.fromarray(rgba)

                    tile_path = os.path.join(output_dir, f"{z}/{tile.x}/{tile.y}.png")
                    os.makedirs(os.path.dirname(tile_path), exist_ok=True)
                    img.save(tile_path)
                except TileOutsideBounds:
                    logger.warning(f"Tile {tile} at zoom level {z} is out of bounds.")
                except Exception as e:
                    logger.error(f"Error generating tile {tile}: {e}")


@app.get("/{z}/{x}/{y}.png")
async def tile(z: int, x: int, y: int):
    """Serve tiles from a local directory."""
    tile_path = f"tiles/{z}/{x}/{y}.png"
    if os.path.exists(tile_path):
        return FileResponse(tile_path)

    # Serve a transparent tile if the requested tile is not found
    logger.warning(f"Tile {z}/{x}/{y} not found.")
    transparent_tile = "transparent_tile.png"
    if not os.path.exists(transparent_tile):
        img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))  # 256x256 transparent tile
        img.save(transparent_tile)
    return FileResponse(transparent_tile)


def start_server():
    """Start the tile server."""
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tile Generator and Server")
    parser.add_argument("--generate", action="store_true", help="Generate tiles from the GeoTIFF.")
    parser.add_argument("--serve", action="store_true", help="Start the tile server.")
    parser.add_argument("--zoom", nargs="+", type=int, help="Zoom levels for tile generation.", default=[15, 16, 17, 18, 19, 20])
    parser.add_argument("--output_dir", type=str, help="Output directory for tiles.", default="tiles")

    args = parser.parse_args()

    if args.generate:
        logger.info("Generating tiles...")
        generate_tiles(GEOTIFF_PATH, args.output_dir, args.zoom)
        logger.info("Tile generation complete.")

    if args.serve:
        logger.info("Starting tile server...")
        start_server()

# Usage:
#-------------
# To generate tiles: 
# python tile_server/main.py --generate --zoom 0 1 2 3 --output_dir tile_server/tiles

# To start server:
# python tile_server/main.py --serve


