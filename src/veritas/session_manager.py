# src/veritas/session_manager.py

import pandas as pd
from typing import Dict, Any, List, Optional

# This class now only imports from its own package, making it portable and testable.
# It has NO dependency on Streamlit.
from .repository import MockDataRepository
from .engine import analytics, plotting, reporting
from . import config

class SessionManager:
    """
    A pure business logic controller for the VERITAS application.

    This class is initialized once per user session and acts as the primary interface
    for the UI to interact with backend business logic and data. It is completely
    decoupled from the Streamlit UI (st) and operates on data it's given or
    retrieves via its repository, making it highly testable and maintainable.
    """
    def __init__(self, repository: MockDataRepository):
        """
        Initializes the SessionManager with a data repository.

        Args:
            repository (MockDataRepository): An instance of a data repository.
                                             This can be swapped for a real DB repository.
        """
        self._repo = repository
        self.settings = config.config  # Use the imported config singleton

    def get_data(self, key: str) -> pd.DataFrame:
        """
        Retrieves a complete dataset via the repository.

        Args:
            key (str): The key for the data to retrieve (e.g., 'hplc', 'deviations').

        Returns:
            pd.DataFrame: A pandas DataFrame containing the requested data.
        """
        return self._repo.get_data(key)

    def get_user_action_items(self, user_role: str) -> List[Dict]:
        """
        Retrieves a list of action items for a user based on their role.

        Args:
            user_role (str): The role of the current user (e.g., 'QC Analyst').

        Returns:
            List[Dict]: A list of action item dictionaries for the UI to render.
        """
        items = []
        if user_role in ["QC Analyst", "DTE Leadership"]:
            deviations_df = self.get_data('deviations')
            if not deviations_df.empty:
                open_dev_count = len(deviations_df[deviations_df['status'] == 'Open'])
                if open_dev_count > 0:
                    items.append({
                        "title": "New Deviations",
                        "details": f"{open_dev_count} require initial assessment.",
                        "icon": "📌",
                        "page_link": "pages/6_Deviation_Hub.py"
                    })
        # Extend with more role-based logic as needed
        return items

    def create_deviation_from_qc(self, report_df: pd.DataFrame, study_id: str, username: str) -> str:
        """
        Creates a new deviation record based on a QC report and logs the action.

        Args:
            report_df (pd.DataFrame): DataFrame of QC discrepancies.
            study_id (str): The ID of the study where discrepancies were found.
            username (str): The user creating the deviation.

        Returns:
            str: The ID of the newly created deviation.
        """
        if report_df.empty or not study_id or not username:
            raise ValueError("report_df, study_id, and username must be provided and valid.")

        title = f"QC Discrepancies found in Study {study_id}"
        linked_record = f"QC_REPORT_{pd.Timestamp.now(tz='UTC').strftime('%Y%m%d%H%M%S')}"
        
        new_dev_id = self._repo.create_deviation(title, linked_record, "High")
        self._repo.write_audit_log(
            user=username,
            action="Deviation Created",
            details=f"Auto-created {new_dev_id} from QC Integrity Center for study '{study_id}'.",
            record_id=new_dev_id
        )
        return new_dev_id

    def advance_deviation_status(self, dev_id: str, current_status: str, username: str) -> None:
        """
        Advances a deviation to its next status in the Kanban workflow.

        Args:
            dev_id (str): The ID of the deviation to advance.
            current_status (str): The current status of the deviation.
            username (str): The user performing the action.
        """
        states = self.settings.app.deviation_management.kanban_states
        if current_status not in states:
            raise ValueError(f"Invalid current status: {current_status}")
        
        current_index = states.index(current_status)
        if current_index + 1 >= len(states):
            raise ValueError(f"Cannot advance status: '{current_status}' is the final state.")

        new_status = states[current_index + 1]
        self._repo.update_deviation_status(dev_id, new_status)
        self._repo.write_audit_log(
            user=username,
            action="Deviation Status Changed",
            details=f"Status for {dev_id} changed from '{current_status}' to '{new_status}'.",
            record_id=dev_id
        )

    def get_deviation_details(self, dev_id: str) -> pd.DataFrame:
        """Retrieves all details for a single deviation ID."""
        all_devs = self.get_data('deviations')
        return all_devs[all_devs['id'] == dev_id]

    def get_signatures_log(self) -> pd.DataFrame:
        """Filters the main audit log for signature-related events."""
        audit_log = self.get_data('audit')
        if audit_log.empty:
            return pd.DataFrame()
            
        sig_keywords = ['Signature', 'Signed', 'E-Sign']
        mask = audit_log['action'].str.contains('|'.join(sig_keywords), case=False, na=False)
        return audit_log[mask]

    def generate_draft_report(self, report_params: Dict) -> Dict:
        """
        Orchestrates the generation of a draft report (PDF or PPT).

        Args:
            report_params (Dict): A dictionary containing all necessary parameters,
                                  e.g., 'report_df', 'study_id', 'report_format', 'cqa'.

        Returns:
            Dict: A dictionary with the generated report's filename, mime type, and bytes.
        """
        # Unpack and validate parameters
        report_df = report_params.get('report_df')
        study_id = report_params.get('study_id')
        report_format = report_params.get('report_format')
        cqa = report_params.get('cqa')
        sections_config = report_params.get('sections_config')
        commentary = report_params.get('commentary')

        if not all([isinstance(report_df, pd.DataFrame), study_id, report_format, cqa, sections_config, commentary]):
            raise ValueError("One or more required parameters for report generation are missing.")

        # Prepare data for the reporting engine
        specs = self.settings.app.process_capability.spec_limits.get(cqa)
        if not specs:
            raise ValueError(f"No specification limits found for CQA '{cqa}'.")
            
        lsl, usl = specs.lsl, specs.usl
        cpk_value = analytics.calculate_cpk(report_df[cqa], lsl, usl)
        cpk_target = self.settings.app.process_capability.cpk_target

        report_data = {
            'study_id': study_id,
            'commentary': commentary,
            'sections_config': sections_config,
            'data': report_df,
            'cqa': cqa,
            'plot_fig': plotting.plot_process_capability(report_df, cqa, lsl, usl, cpk_value, cpk_target)
        }

        if report_format == 'PDF':
            file_bytes = reporting.generate_pdf_report(report_data, watermark="DRAFT")
            filename = f"DRAFT_VERITAS_Summary_{study_id}_{cqa}.pdf"
            mime = "application/pdf"
        elif report_format == 'PowerPoint':
            file_bytes = reporting.generate_ppt_report(report_data)
            filename = f"DRAFT_VERITAS_PPT_{study_id}_{cqa}.pptx"
            mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        else:
            raise ValueError(f"Unsupported report format: {report_format}")

        # The manager returns a complete artifact; the UI layer handles storing it in session state.
        return {
            'filename': filename, 'mime': mime, 'bytes': file_bytes,
            'report_data': report_data  # Pass along the data for the final signing step
        }

    def finalize_and_sign_report(self, draft_report_data: Dict, signing_reason: str, username: str) -> Dict:
        """
        Applies a signature to the report data, regenerates the final PDF, and logs the event.

        Args:
            draft_report_data (Dict): The 'report_data' dictionary from the draft generation step.
            signing_reason (str): The reason for the electronic signature.
            username (str): The user applying the signature.

        Returns:
            Dict: A dictionary with the final report's filename, mime type, and bytes.
        """
        final_filename = f"FINAL_VERITAS_Summary_{draft_report_data['study_id']}.pdf"
        signature_details = {
            'user': username,
            'timestamp': pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d %H:%M:%S UTC'),
            'reason': signing_reason
        }
        draft_report_data['signature_details'] = signature_details
        
        # Regenerate the PDF, this time without the watermark and with the signature block
        final_bytes = reporting.generate_pdf_report(draft_report_data)
        
        self._repo.write_audit_log(
            user=username,
            action="E-Signature Applied",
            details=f"Signed report for study '{draft_report_data['study_id']}' for reason: '{signing_reason}'.",
            record_id=draft_report_data['study_id']
        )
        
        return {
            'filename': final_filename,
            'final_bytes': final_bytes,
            'mime': 'application/pdf'
        }

    def get_kpi(self, kpi_name: str) -> Dict:
        """
        Calculates and retrieves a specific Key Performance Indicator (KPI).

        Args:
            kpi_name (str): The unique name of the KPI.

        Returns:
            Dict: A dictionary containing the KPI's value, delta, and help text.
        """
        if kpi_name == 'active_deviations':
            df = self.get_data('deviations')
            value = len(df[df['status'] != 'Closed']) if not df.empty else 0
            return {'value': value, 'delta': None, 'sme_info': "Total number of open quality events."}
        
        if kpi_name == 'data_quality_score':
            df = self.get_data('hplc')
            score = 100 * (1 - (df.isnull().sum().sum() / df.size)) if not df.empty else 100
            return {'value': score, 'delta': round(score - 99.5, 1), 'sme_info': "Percentage of non-null data points. Target: 99.5%"}
        
        if kpi_name == 'first_pass_yield':
            # Placeholder logic for demonstration
            return {'value': 92.1, 'delta': 2.1, 'sme_info': "Percentage of processes completing without deviations. Target: 90%"}
        
        if kpi_name == 'mean_time_to_resolution':
            # Placeholder logic for demonstration
            return {'value': 4.5, 'delta': -0.5, 'sme_info': "Average business days to close a deviation. Target: 5 days"}
        
        raise ValueError(f"Unknown KPI: {kpi_name}")

    def get_risk_matrix_data(self) -> pd.DataFrame:
        """Retrieves data formatted for the program risk matrix plot."""
        # This would typically involve complex logic joining multiple data sources.
        # Using placeholder data for this demonstration.
        return pd.DataFrame({
            "program_id": ["VX-561", "VX-121", "VX-809", "VX-984"],
            "days_to_milestone": [50, 80, 200, 150],
            "dqs": [92, 98, 99, 96],
            "active_deviations": [8, 2, 1, 4],
            "risk_quadrant": ["High Priority", "On Track", "On Track", "Data Risk"]
        })

    def get_pareto_data(self) -> pd.DataFrame:
        """Generates frequency data for a Pareto chart of deviation titles."""
        df = self.get_data('deviations')
        if df.empty or 'title' not in df.columns:
            return pd.DataFrame(columns=['Error Type', 'Frequency'])
        
        # Count the frequency of each distinct title
        pareto_data = df['title'].value_counts().reset_index()
        pareto_data.columns = ['Error Type', 'Frequency']
        return pareto_data.sort_values(by='Frequency', ascending=False)
