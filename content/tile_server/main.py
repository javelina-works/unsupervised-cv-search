import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from rio_tiler.io import COGReader
from rio_tiler.errors import TileOutsideBounds
from PIL import Image
import numpy as np
import uvicorn
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # Output to stdout
    ]
)
logger = logging.getLogger(__name__)
logger.info("Logging initialized.")

app = FastAPI()

# Path to your GeoTIFF
GEOTIFF_PATH = 'tile_server/input/IGNORE_reprojected_region.tif'
transparent_tile = "transparent_tile.png"
oob_tile = "out_of_bounds_tile.png"

# Manual re-color just to see
img = Image.new("RGBA", (256, 256), (255, 0, 0, 128))
img.save(transparent_tile)

img = Image.new("RGBA", (256, 256), (255, 0, 0, 0))
img.save(oob_tile)



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
    logger.info(f"Tile requested: z={z}, x={x}, y={y}")
    sys.stdout.flush()  # Force flush
    
    try:
        tile_path = f"tile_server/tiles/{z}/{x}/{y}.png"
        if os.path.exists(tile_path):
            return FileResponse(tile_path)

        with COGReader(GEOTIFF_PATH) as cog:
            tile_data, mask = cog.tile(x, y, z)
            rgba = np.dstack((tile_data[0], tile_data[1], tile_data[2], mask)).astype(np.uint8)
            img = Image.fromarray(rgba)
            img.save(tile_path)
            logger.info(f"Tile generated: {tile_path}")
            return FileResponse(tile_path)
        
    except TileOutsideBounds:
        logger.warning(f"Tile outside bounds: z={z}, x={x}, y={y}")
        if not os.path.exists(oob_tile):
            img = Image.new("RGBA", (256, 256), (255, 0, 0, 255))
            img.save(oob_tile)
        return FileResponse(oob_tile)
    
    except Exception as e:
        logger.error(f"Error generating tile: {e}")
        if not os.path.exists(transparent_tile):
            img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
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


