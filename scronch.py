#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys
import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
from gi.repository import GLib, GObject
from gi.repository import Gio 
import os
import datetime
import logging

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
            "Duplicate, flatten, and export image as PNG with timestamp",
            name
        )
        procedure.set_attribution("Charon", "Copyleft", "2024")

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

            # Generate the output file path
            now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            png_filename = os.path.join(base_dir, f"{base_filename}-{now}.png")
            logger.debug(f"Output will be saved to: {png_filename}")

            # Absolute file path for saving
            if not os.path.isabs(png_filename):
                png_filename = os.path.abspath(png_filename)

            # Get the PDB instance and export procedure
            pdb = Gimp.get_pdb()
            export_proc = pdb.lookup_procedure("file-png-export")
            if not export_proc:
                raise RuntimeError("Procedure 'file-png-export' not found.")

            # Create a ProcedureConfig object
            config = export_proc.create_config()
            logger.debug("Config object created.")

            # Convert filename to GFile
            gfile = Gio.File.new_for_path(png_filename)
            logger.debug("Filename converted.")

            # Set the required parameters
            config.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
            config.set_property("image", dup_img)
            config.set_property("file", gfile)  # Pass the GFile object
            config.set_property("options", None)  # Structured options
            config.set_property("interlaced", False)
            config.set_property("compression", 9)
            config.set_property("bkgd", True)
            config.set_property("offs", False)
            config.set_property("phys", True)
            config.set_property("time", True)
            config.set_property("save-transparent", True)
            config.set_property("optimize-palette", False)
            config.set_property("format", "auto")
            logger.debug("Properties set.")

            # Run the procedure
            logger.info("Running export procedure...")
            Gimp.message("Running export procedure...")
            result = export_proc.run(config)
            logger.debug("Export procedure run.")
            logger.debug(f"Procedure result: {result}")

            # Extract status from the ValueArray
            status = result.index(0)  # Retrieve the status at index 0
            if status != Gimp.PDBStatusType.SUCCESS:
                raise RuntimeError(f"Export failed with status {status}")
            logger.info(f"Exported to {png_filename}")
            Gimp.message(f"Exported to {png_filename}")

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
