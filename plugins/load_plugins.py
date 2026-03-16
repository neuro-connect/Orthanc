import sys
import os
import orthanc

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# with open(os.path.join(current_dir, "OrthancExplorer.js"), "r") as f:
#     orthanc.ExtendOrthancExplorer(f.read())

# # Add the raster-plugin directory to Python path
# raster_plugin_path = os.path.join(current_dir, "raster-plugin")
# sys.path.append(raster_plugin_path)

# # Import the raster module
# from raster import *

# # Add the raster-plugin directory to Python path
# epinsight_plugin_path = os.path.join(current_dir, "epinsight-plugin")
# sys.path.append(epinsight_plugin_path)

# # Import the epinsight module
# from epinsight import *

# Add the surgeryflow-plugin directory to Python path
surgeryflow_plugin_path = os.path.join(current_dir, "surgeryflow-plugin")
sys.path.append(surgeryflow_plugin_path)

# Import the epinsight module
from surgeryflow import *
