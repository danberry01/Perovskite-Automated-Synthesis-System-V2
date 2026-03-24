from .file_manager_frame import FileManagerFrame
from .info_frame import InfoFrame
from .settings_frame import SettingsFrame
from .tab_manager_frame import TabManagerFrame
from .tab_view_frame import TabViewFrame

from .procedure_builder import *
from .procedure_viewer import *

PROCEDURE_BUILDER = [
    "ConnectionFrame",
    "LocationsFrame",
    "ProcedureBuilderFrame"
]

PROCEDURE_VIEWER = [
    "CameraFrame",
    "ConsoleFrame",
    "ProcedureQueueFrame",
    "ProcedureViewerFrame",
    "SpectrometerFrame"
]