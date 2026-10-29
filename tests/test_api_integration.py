"""Depodaki örnek veri ve eğitilmiş modelle, dış ağa çıkmadan API doğrulaması."""

from sqlalchemy import text
import sys
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from fastapi.testclient import TestClient
from app.ai import decision_engine as engine_module
from app.ai.predictor import predictor
from app.ai.train_forecast import load_and_preprocess_data
from app.main import app


class SampleDataIntegrationTests(unittest.TestCase):
    def test_all_endpoints_with_real_model_and_reconciled_training_data(self):
        frame = load_and_preprocess_data()
        with engine_module._engine().connect() as conn:
            count, revenue = conn.execute(text('SELECT COUNT(*), SUM(total_amount) FROM orders')).one()
        self.assertEqual(int(frame.order_count.sum()), count)
        self.assertEqual(float(frame.total_revenue.sum()), revenue)
        weather = {
            'temperature': 18, 'weather': 'Güneşli',
            'description': '18°C (test)', 'is_live': False,
        }
        with patch.object(engine_module, 'get_current_weather', return_value=weather), TestClient(app) as client:
            for url in ['/', '/api/ai/sales-summary', '/api/ai/traffic-forecast',
                        '/api/ai/stock-status', '/api/ai/daily-brief']:
                with self.subTest(url=url):
                    self.assertEqual(client.get(url).status_code, 200)
            response = client.post('/api/ai/query', json={'query': 'bugünkü ciro nedir'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['intent'], 'SALES_SUMMARY')
        self.assertEqual(predictor.package['data_summary']['revenue_aggregation'], 'once_per_order')


if __name__ == '__main__':
    unittest.main()
