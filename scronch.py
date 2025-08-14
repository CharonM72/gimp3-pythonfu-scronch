#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 3 of the License, or
#   (at your option) any later version.

import sys
import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
from gi.repository import GLib, GObject
from gi.repository import Gio 
import os
import datetime
import logging

# ============================================================================
# EXPORT SETTINGS - Modify these values to customize export behavior
# ============================================================================

# AVIF Export Settings
AVIF_QUALITY = 85                   # Quality factor (0 = worst, 100 = best) (0 <= quality <= 100, default 50)
AVIF_LOSSLESS = True                # Use lossless compression (TRUE or FALSE, default FALSE)
AVIF_BIT_DEPTH = 10                 # 8, 10, or 12 bits per channel
AVIF_PIXEL_FORMAT = "yuv444"        # "rgb", "yuv444" (best quality), "yuv420" (smaller)
AVIF_ENCODER_SPEED = "balanced"     # "slow" (best compression), "balanced", "fast"
AVIF_INCLUDE_EXIF = True            # Include EXIF metadata
AVIF_INCLUDE_XMP = True             # Include XMP metadata

# PNG Export Settings (fallback)
PNG_COMPRESSION = 9                 # Deflate Compression factor (0..9) (0 <= compression <= 9, default 9)
PNG_INTERLACED = False              # Use Adam7 interlacing (TRUE or FALSE, default FALSE)
PNG_SAVE_TRANSPARENT = True         # Preserve color of completely transparent pixels (TRUE or FALSE, default FALSE)
PNG_OPTIMIZE_PALETTE = False        # When checked, save as 1, 2, 4, or 8-bit depending on number of colors used. When unchecked, always save as 8-bit (TRUE or FALSE, default FALSE)
PNG_FORMAT = "auto"                 # Allowed values: auto: Automatic, rgb8: 8 bpc RGB, gray8: 8 bpc GRAY, rgba8: 8 bpc RGBA, graya8: 8 bpc GRAYA, rgb16: 16 bpc RGB,gray16: 16 bpc GRAY, rgba16: 16 bpc RGBA, graya16: 16 bpc GRAYA

# General Settings
PREFER_AVIF = True                  # Set to False to always use PNG instead
TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"   # Timestamp format for filename

# ============================================================================

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScronchPlugin(Gimp.PlugIn):
    def do_set_i18n(self, procname):
        return False
    
    def do_query_procedures(self):
        return ["scronch"]

    def do_create_procedure(self, name):
        procedure = Gimp.ImageProcedure.new(
            self,
            name,
            Gimp.PDBProcType.PLUGIN,
            self.run,
            None,
        )
        procedure.set_image_types("*")
        procedure.set_menu_label("Scronch")
        procedure.add_menu_path('<Image>/Filters/')
        procedure.set_documentation(
            "Scronch plugin",
            "Duplicate, flatten, and export image as AVIF or PNG with timestamp. Settings in the .py plugin file.",
            name
        )
        procedure.set_attribution("Charon", "GPL 3", "2025")

        return procedure

    def run(self, procedure, run_mode, image, drawable, parameters, run_data):
        try:
            # Duplicate the image
            dup_img = image.duplicate()
            logger.debug("Image duplicated.")

            # Flatten the layers in the duplicate
            dup_img.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)
            logger.debug("Image flattened.")

            # Determine the directory and base name for the output file
            file_obj = image.get_file()
            if file_obj:
                original_filepath = file_obj.get_path()
                if original_filepath:
                    base_dir = os.path.dirname(original_filepath)
                    base_filename, _ = os.path.splitext(os.path.basename(original_filepath))
                else:
                    base_dir = os.getcwd()
                    base_filename = "untitled"
            else:
                base_dir = os.getcwd()
                base_filename = "untitled"

            # Generate the output file path (changed to .avif)
            now = datetime.datetime.now().strftime(TIMESTAMP_FORMAT)
            if PREFER_AVIF:
                output_filename = os.path.join(base_dir, f"{base_filename}-{now}.avif")
            else:
                output_filename = os.path.join(base_dir, f"{base_filename}-{now}.png")
            logger.debug(f"Output will be saved to: {output_filename}")

            # Absolute file path for saving
            if not os.path.isabs(output_filename):
                output_filename = os.path.abspath(output_filename)

            # Get the PDB instance and export procedure
            pdb = Gimp.get_pdb()
            
            # Try AVIF first if preferred, otherwise use PNG
            if PREFER_AVIF:
                export_proc = pdb.lookup_procedure("file-heif-av1-export")
                if not export_proc:
                    logger.warning("AVIF export not available, falling back to PNG")
                    export_proc = pdb.lookup_procedure("file-png-export")
                    output_filename = output_filename.replace('.avif', '.png')
            else:
                export_proc = pdb.lookup_procedure("file-png-export")
            
            if not export_proc:
                raise RuntimeError("No suitable export procedure found.")

            # Create a ProcedureConfig object
            config = export_proc.create_config()
            logger.debug("Config object created.")

            # Convert filename to GFile
            gfile = Gio.File.new_for_path(output_filename)
            logger.debug("Filename converted.")

            # Set AVIF-specific parameters (if using AVIF export)
            if "heif-av1" in export_proc.get_name():
                logger.info("Setting AVIF parameters...")
                
                # Set the required base parameters first
                config.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
                config.set_property("image", dup_img)
                config.set_property("file", gfile)
                
                # Set AVIF-specific parameters using variables
                config.set_property("options", None)
                config.set_property("quality", AVIF_QUALITY)
                config.set_property("lossless", AVIF_LOSSLESS)
                config.set_property("save-bit-depth", AVIF_BIT_DEPTH)
                config.set_property("pixel-format", AVIF_PIXEL_FORMAT)
                config.set_property("encoder-speed", AVIF_ENCODER_SPEED)
                config.set_property("include-exif", AVIF_INCLUDE_EXIF)
                config.set_property("include-xmp", AVIF_INCLUDE_XMP)
                
                logger.info(f"AVIF parameters: quality={AVIF_QUALITY}, lossless={AVIF_LOSSLESS}, "
                           f"bit-depth={AVIF_BIT_DEPTH}, pixel-format={AVIF_PIXEL_FORMAT}, "
                           f"speed={AVIF_ENCODER_SPEED}")
                        
            else:
                # PNG fallback parameters using variables
                logger.info("Using PNG export parameters...")
                config.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
                config.set_property("image", dup_img)
                config.set_property("file", gfile)
                config.set_property("options", None)
                config.set_property("interlaced", PNG_INTERLACED)
                config.set_property("compression", PNG_COMPRESSION)
                config.set_property("bkgd", True)
                config.set_property("offs", False)
                config.set_property("phys", True)
                config.set_property("time", True)
                config.set_property("save-transparent", PNG_SAVE_TRANSPARENT)
                config.set_property("optimize-palette", PNG_OPTIMIZE_PALETTE)
                config.set_property("format", PNG_FORMAT)
                
                logger.info(f"PNG parameters: compression={PNG_COMPRESSION}, "
                           f"transparent={PNG_SAVE_TRANSPARENT}, format={PNG_FORMAT}")

            logger.debug("Properties set.")

            # Run the procedure
            logger.info("Running export procedure...")
            Gimp.message("Running export procedure...")
            result = export_proc.run(config)
            logger.debug("Export procedure run.")
            logger.debug(f"Procedure result: {result}")

            # Extract status from the ValueArray
            status = result.index(0)
            if status != Gimp.PDBStatusType.SUCCESS:
                raise RuntimeError(f"Export failed with status {status}")
            
            logger.info(f"Exported to {output_filename}")
            Gimp.message(f"Exported to {output_filename}")

            # Delete the duplicate image
            dup_img.delete()

            # Return success status
            return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)

        except Exception as e:
            # Log the error and return failure status
            Gimp.message(f"Scronch plugin error: {str(e)}")
            logger.error(f"Scronch plugin error: {str(e)}", exc_info=True)
            return procedure.new_return_values(Gimp.PDBStatusType.EXECUTION_ERROR, None)

Gimp.main(ScronchPlugin.__gtype__, sys.argv)