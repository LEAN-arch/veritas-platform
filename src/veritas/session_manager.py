# src/veritas/session_manager.py

import pandas as pd
from .repository import MockDataRepository
from .engine import analytics, plotting, reporting
from . import config

class SessionManager:
    """
    A pure business logic controller for the VERITAS application.
    It is initialized once per session and contains no Streamlit-specific code.
    """
    def __init__(self, repository: MockDataRepository):
        self._repo = repository
        self.settings = config.config # Use the simplified config

    def get_data(self, key: str) -> pd.DataFrame:
        """Retrieves data via the repository."""
        return self._repo.get_data(key)

    def get_user_action_items(self, user_role: str) -> list:
        """Retrieves action items based on user role and current data state."""
        items = []
        if user_role == "DTE Leadership":
            deviations = self.get_data('deviations')
            open_devs = len(deviations[deviations['status'] != 'Closed'])
            if open_devs > 0:
                items.append({
                    "title": "Open Deviations",
                    "details": f"{open_devs} require attention.",
                    "icon": "📌",
                    "page_link": "pages/5_Deviation_Hub.py"
                })
        # ... other role-based action items ...
        return items

    def get_deviation_details(self, dev_id: str) -> pd.DataFrame:
        """Retrieves details for a specific deviation."""
        all_devs = self.get_data('deviations')
        return all_devs[all_devs['id'] == dev_id]

    # ... The rest of the business logic methods from the original SessionManager ...
    # (e.g., create_deviation_from_qc, advance_deviation_status, get_kpi, etc.)
    # They are refactored to be pure functions that operate on data and return
    # results, without touching st.session_state.
