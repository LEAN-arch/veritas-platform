# src/veritas/repository.py

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MockDataRepository:
    """
    A mock data repository for the VERITAS application.

    This class simulates a data access layer, providing predictable and consistent
    datasets for development and testing. It ensures that the application's business
    logic can be developed independently of a live database connection.
    """
    def __init__(self, seed: int = 42):
        """
        Initializes the repository and generates all mock datasets.

        Args:
            seed (int): A random seed to ensure reproducibility of generated data.
        """
        self._seed = seed
        self._rng = np.random.default_rng(self._seed)
        self._cache: Dict[str, pd.DataFrame] = {}
        logger.info(f"MockDataRepository initialized with seed {self._seed}")
        self._generate_all_data()

    def _generate_all_data(self) -> None:
        """Generates all mock datasets and stores them in an internal cache."""
        self._cache['hplc'] = self._generate_hplc_data()
        self._cache['deviations'] = self._generate_deviations_data()
        self._cache['stability'] = self._generate_stability_data()
        self._cache['audit'] = self._generate_audit_log()
        logger.info("All mock datasets have been generated and cached.")

    def get_data(self, data_type: str) -> pd.DataFrame:
        """
        Retrieves a copy of a dataset by its key.

        Args:
            data_type (str): The key of the dataset to retrieve (e.g., 'hplc').

        Returns:
            pd.DataFrame: A copy of the requested dataset.

        Raises:
            ValueError: If the requested data_type is unknown.
        """
        if data_type not in self._cache:
            raise ValueError(f"Unknown data_type: {data_type}. Available types: {list(self._cache.keys())}")
        return self._cache[data_type].copy()

    def _generate_hplc_data(self) -> pd.DataFrame:
        """Generates mock HPLC data."""
        num_records = 150
        data = {
            'sample_id': [f'SMPL-{2024000 + i}' for i in range(num_records)],
            'batch_id': self._rng.choice([f'B{101 + i}' for i in range(5)], size=num_records),
            'instrument_id': self._rng.choice(['HPLC-01', 'HPLC-02', 'HPLC-03'], size=num_records),
            'analyst': self._rng.choice(['j.doe', 'p.smith', 's.jones'], size=num_records),
            'injection_time': pd.to_datetime(pd.to_datetime('2024-01-01') + pd.to_timedelta(self._rng.randint(1, 180, size=num_records), unit='D')),
            'purity': self._rng.normal(loc=99.8, scale=0.5, size=num_records).round(2),
            'main_impurity': self._rng.normal(loc=0.15, scale=0.05, size=num_records).round(3),
            'bio_activity': self._rng.normal(loc=102.0, scale=3.0, size=num_records).round(1)
        }
        df = pd.DataFrame(data)
        # Inject some predictable drift for testing ANOVA
        df.loc[df['instrument_id'] == 'HPLC-03', 'purity'] -= 0.75
        # Inject some nulls for testing QC
        df.loc[df.sample(n=5, random_state=self._seed).index, 'purity'] = np.nan
        return df

    def _generate_deviations_data(self) -> pd.DataFrame:
        """Generates mock quality deviations data."""
        num_records = 12
        statuses = ['Open', 'In Progress', 'Under Review', 'Closed']
        data = {
            'id': [f'DEV-{2400 + i}' for i in range(num_records)],
            'status': self._rng.choice(statuses, size=num_records, p=[0.2, 0.3, 0.1, 0.4]),
            'title': self._rng.choice([
                "OOS Result Found", "Instrument Drift Detected", "Specification Breach",
                "Contamination Event", "Missing Sample Log"
            ], size=num_records),
            'priority': self._rng.choice(['High', 'Medium', 'Low'], size=num_records, p=[0.3, 0.5, 0.2]),
            'linked_record': self._rng.choice(self._cache['hplc']['sample_id'].tolist() + ['HPLC-02'], size=num_records),
            'rca_problem': ['' for _ in range(num_records)],
            'rca_5whys': ['' for _ in range(num_records)],
            'capa_corrective': ['' for _ in range(num_records)],
            'capa_preventive': ['' for _ in range(num_records)],
        }
        return pd.DataFrame(data)

    def _generate_stability_data(self) -> pd.DataFrame:
        """Generates mock stability study data."""
        lots = ['LOTA-001', 'LOTA-002', 'LOTB-001']
        timepoints = [0, 3, 6, 9, 12, 18, 24]
        records = []
        for lot in lots:
            initial_purity = self._rng.uniform(99.5, 99.9)
            degradation_rate = self._rng.uniform(0.04, 0.08)
            if lot == 'LOTA-002': # Make one lot degrade faster for poolability tests
                degradation_rate *= 2
            for t in timepoints:
                records.append({
                    'product_id': lot.split('-')[0],
                    'lot_id': lot,
                    'timepoint_months': t,
                    'purity': round(initial_purity - degradation_rate * t + self._rng.normal(0, 0.1), 2),
                    'main_impurity': round(0.1 + degradation_rate * t / 2 + self._rng.normal(0, 0.05), 3)
                })
        return pd.DataFrame(records)

    def _generate_audit_log(self) -> pd.DataFrame:
        """Generates a mock audit log."""
        num_records = 200
        data = {
            'timestamp': pd.to_datetime('2024-01-01') + pd.to_timedelta(np.arange(num_records) * 8, unit='h'),
            'user': self._rng.choice(['j.doe', 'p.smith', 's.jones', 'system'], size=num_records, p=[0.4, 0.3, 0.2, 0.1]),
            'action': self._rng.choice([
                "Data Entry", "Data Update", "User Login", "Report Generated",
                "Deviation Created", "E-Signature Applied"
            ], size=num_records),
            'record_id': self._rng.choice(self._cache['hplc']['sample_id'].tolist()[:50] + self._cache['deviations']['id'].tolist(), size=num_records),
            'details': "Action performed as per standard procedure."
        }
        return pd.DataFrame(data)

    def write_audit_log(self, user: str, action: str, details: str, record_id: Optional[str] = None) -> None:
        """
        Simulates writing a new entry to the audit log.

        Args:
            user (str): The user performing the action.
            action (str): The action being performed.
            details (str): A description of the action.
            record_id (Optional[str]): The ID of the record being affected.
        """
        new_entry = pd.DataFrame([{
            'timestamp': pd.Timestamp.now(tz='UTC'),
            'user': user,
            'action': action,
            'record_id': record_id,
            'details': details
        }])
        self._cache['audit'] = pd.concat([self._cache['audit'], new_entry], ignore_index=True)
        logger.info(f"AUDIT LOG: User '{user}' performed action '{action}'.")

    def create_deviation(self, title: str, linked_record: str, priority: str) -> str:
        """Simulates creating a new deviation record."""
        new_id = f"DEV-{2400 + len(self._cache['deviations'])}"
        new_entry = pd.DataFrame([{
            'id': new_id,
            'status': 'Open',
            'title': title,
            'priority': priority,
            'linked_record': linked_record,
            'rca_problem': '', 'rca_5whys': '', 'capa_corrective': '', 'capa_preventive': ''
        }])
        self._cache['deviations'] = pd.concat([self._cache['deviations'], new_entry], ignore_index=True)
        return new_id

    def update_deviation_status(self, dev_id: str, new_status: str) -> None:
        """Simulates updating the status of a deviation."""
        self._cache['deviations'].loc[self._cache['deviations']['id'] == dev_id, 'status'] = new_status
