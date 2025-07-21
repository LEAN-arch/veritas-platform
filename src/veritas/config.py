# src/veritas/config.py

import logging

logger = logging.getLogger(__name__)

class _Limits:
    """A simple class to hold LSL and USL values."""
    def __init__(self, lsl: float, usl: float):
        self.lsl = lsl
        self.usl = usl

class _ProcessCapabilitySettings:
    """Configuration for the Process Capability and related modules."""
    def __init__(self):
        self.available_cqas = ['purity', 'main_impurity', 'bio_activity']
        self.spec_limits = {
            'purity': _Limits(lsl=98.0, usl=102.0),
            'main_impurity': _Limits(lsl=0.0, usl=0.5),
            'bio_activity': _Limits(lsl=90.0, usl=110.0),
        }
        self.cpk_target = 1.33

class _StabilitySettings:
    """Configuration for the Stability Program module."""
    def __init__(self):
        self.spec_limits = {
            'purity': _Limits(lsl=98.0, usl=None),  # Degrading product, only LSL matters
            'main_impurity': _Limits(lsl=None, usl=0.75), # Impurity grows, only USL matters
        }

class _DeviationManagementSettings:
    """Configuration for the Deviation Management Hub."""
    def __init__(self):
        self.kanban_states = ['Open', 'In Progress', 'Under Review', 'Closed']

class _PlottingColors:
    """Centralized color theme for plots."""
    def __init__(self):
        self.blue = "#1f77b4"
        self.orange = "#ff7f0e"
        self.green = "#2ca02c"
        self.red = "#d62728"
        self.purple = "#9467bd"
        self.gray = "#7f7f7f"
        self.lightcyan = "#e0f2f1"
        self.lightblue = "#aec7e8"


class _AppSettings:
    """A container for all module-specific settings."""
    def __init__(self):
        self.process_capability = _ProcessCapabilitySettings()
        self.stability_specs = _StabilitySettings()
        self.deviation_management = _DeviationManagementSettings()

class _VeritasConfig:
    """
    The main configuration class for the VERITAS application.

    This acts as a singleton that holds all application settings.
    """
    def __init__(self):
        try:
            self.app = _AppSettings()
            self.COLORS = _PlottingColors()
            logger.info("Application configuration loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize AppConfig: {e}", exc_info=True)
            raise RuntimeError(f"AppConfig initialization failed: {e}")

# --- Singleton Instance ---
# This creates a single, immutable instance of the configuration that can be
# imported anywhere in the application without risk of modification.
try:
    config = _VeritasConfig()
except Exception as e:
    # This is a critical failure; the app cannot run without its config.
    logger.critical(f"FATAL: Could not create the application config singleton: {e}", exc_info=True)
    raise
