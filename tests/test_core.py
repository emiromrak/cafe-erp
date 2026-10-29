"""Karar destek çekirdeğinin ciro, hata ve erişim kuralları için regresyon testleri."""

import io
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing, redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from fastapi.testclient import TestClient
from app.ai import decision_engine as engine_module
from app.ai import weather_service
from app.ai.predictor import DemandPredictor, ForecastUnavailableError
from app.ai.telegram_bot import CafeTelegramBot
from app.ai.train_forecast import load_and_preprocess_data
from app.main import app


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / 'test.db'
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.executescript('''
                CREATE TABLE orders (
                    order_id TEXT PRIMARY KEY, timestamp TEXT, weekday TEXT,
                    weather TEXT, temperature INTEGER, payment_method TEXT, total_amount REAL
                );
                CREATE TABLE order_items (
                    order_id TEXT, product_id TEXT, product_name TEXT,
                    quantity INTEGER, unit_price REAL
                );
            ''')
        self.engine = engine_module.CafeDecisionEngine()
        self.db_patch = patch.object(engine_module, 'DB_PATH', self.db_path)
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)

    def seed_orders(self):
        """Eşit tutarlı iki adisyon, çok kalemli ve kalemsiz kayıtları kapsar."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.executemany('INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)', [
                ('a', '2020-01-01 08:10:00', 'Wednesday', 'Güneşli', 18, 'Nakit', 100),
                ('b', '2020-01-01 08:20:00', 'Wednesday', 'Güneşli', 18, 'Kredi Kartı', 100),
                ('c', '2020-01-01 09:00:00', 'Wednesday', 'Güneşli', 18, 'Nakit', 50),
            ])
            conn.executemany('INSERT INTO order_items VALUES (?, ?, ?, ?, ?)', [
                ('a', 'prod_tea_glass', 'Çay', 2, 25),
                ('a', 'prod_toast_cheese', 'Tost', 1, 50),
                ('b', 'prod_latte', 'Latte', 1, 100),
            ])
            conn.commit()

    def test_training_counts_each_order_once_and_preserves_quantities(self):
        self.seed_orders()
        frame = load_and_preprocess_data(self.db_path)
        self.assertEqual(frame['total_revenue'].sum(), 250)
        self.assertEqual(frame['order_count'].sum(), 3)
        self.assertEqual(frame['tea_qty'].sum(), 2)
        self.assertEqual(frame['toast_qty'].sum(), 1)
        self.assertEqual(frame['hot_coffee_qty'].sum(), 1)
        self.assertEqual(frame.iloc[0]['total_revenue'], 200)

    def test_empty_training_has_clear_error(self):
        with self.assertRaisesRegex(ValueError, 'sipariş verisi bulunamadı'):
            load_and_preprocess_data(self.db_path)

    def test_sales_cash_and_card_reconcile(self):
        self.seed_orders()
        stats = self.engine.get_sales_summary('2020-01-01')['stats']
        self.assertEqual(stats['total_revenue'], 250)
        self.assertEqual(stats['total_orders'], 3)
        self.assertEqual(stats['cash_revenue'] + stats['card_revenue'], stats['total_revenue'])

    def test_empty_database_returns_zero_without_fallback(self):
        report = self.engine.get_sales_summary()
        self.assertEqual(report['query_date'], datetime.now().strftime('%Y-%m-%d'))
        self.assertFalse(report['is_fallback'])
        self.assertTrue(all(value == 0 for value in report['stats'].values()))
        self.assertEqual(report['top_items'], [])

    def test_explicit_today_does_not_fallback(self):
        self.seed_orders()
        report = self.engine.get_sales_summary(datetime.now().strftime('%Y-%m-%d'))
        self.assertFalse(report['is_fallback'])
        self.assertEqual(report['stats']['total_revenue'], 0)

    def test_unspecified_date_uses_latest_active_day(self):
        self.seed_orders()
        report = self.engine.get_sales_summary()
        self.assertTrue(report['is_fallback'])
        self.assertEqual(report['query_date'], '2020-01-01')

    def test_connections_close_even_when_query_fails(self):
        conn = sqlite3.connect(':memory:')
        with patch.object(engine_module, 'get_db_connection', return_value=conn):
            with self.assertRaises(sqlite3.OperationalError):
                self.engine.get_sales_summary()
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute('SELECT 1')

    def test_api_validates_dates_and_handles_empty_sales(self):
        with TestClient(app) as client:
            self.assertEqual(client.get('/api/ai/sales-summary?date=bad-date').status_code, 422)
            result = client.get('/api/ai/sales-summary?date=2020-01-01')
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()['stats']['total_revenue'], 0)

    def test_missing_model_does_not_break_sales_and_returns_503_for_forecasts(self):
        predictor = DemandPredictor(Path(self.temp.name) / 'missing.pkl')
        with patch.object(engine_module.decision_engine, 'predictor', predictor), \
             patch.object(engine_module, 'get_current_weather', return_value={
                 'temperature': 18, 'weather': 'Güneşli', 'description': 'Test',
             }), TestClient(app) as client:
            self.assertEqual(client.get('/api/ai/sales-summary').status_code, 200)
            response = client.get('/api/ai/traffic-forecast')
            self.assertEqual(response.status_code, 503)
            self.assertIn('yeniden eğitin', response.json()['detail'])


class ForecastTests(unittest.TestCase):
    def test_corrupt_model_has_clear_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'invalid.pkl'
            path.write_bytes(b'not a model')
            with self.assertRaises(ForecastUnavailableError):
                DemandPredictor(path).predict_hour(8, 0, 'Güneşli', 18)

    def test_burn_rate_preserves_stock_and_reports_first_depletion_only(self):
        predictor = DemandPredictor()
        stocks = {'rm_tea_leaf': 7.0}
        def forecast(hour, *args):
            return {
                'hour': hour, 'predicted_traffic': 1, 'predicted_tea_glasses': 1,
                'predicted_toasts': 0, 'predicted_hot_coffee': 0, 'predicted_revenue': 25,
            }
        with patch.object(predictor, 'predict_hour', side_effect=forecast):
            result = predictor.simulate_day_burn_rate(0, 'Güneşli', 18, stocks)
        self.assertEqual(stocks['rm_tea_leaf'], 7.0)
        self.assertEqual(len(result['alerts']), 1)
        self.assertEqual(result['alerts'][0]['run_out_hour'], '10:00')
        self.assertEqual(result['summary']['total_estimated_revenue'], 375)


class WeatherTests(unittest.TestCase):
    def test_coordinates_come_from_configuration(self):
        response = Mock(status_code=200)
        response.json.return_value = {'current_weather': {
            'temperature': 14, 'windspeed': 10, 'weathercode': 61,
        }}
        with patch.dict(os.environ, {'CAFE_LATITUDE': '37.7', 'CAFE_LONGITUDE': '30.5'}), \
             patch.object(weather_service.requests, 'get', return_value=response) as request:
            weather = weather_service.get_current_weather()
        self.assertIn('latitude=37.7&longitude=30.5', request.call_args.args[0])
        self.assertTrue(weather['is_live'])
        self.assertEqual(weather['weather'], 'Yağmurlu')

    def test_missing_weather_is_not_presented_as_live(self):
        response = Mock(status_code=200)
        response.json.return_value = {}
        with patch.object(weather_service.requests, 'get', return_value=response):
            self.assertFalse(weather_service.get_current_weather()['is_live'])

    def test_network_failure_uses_fallback(self):
        with patch.object(weather_service.requests, 'get', side_effect=OSError):
            self.assertFalse(weather_service.get_current_weather()['is_live'])


class TelegramTests(unittest.TestCase):
    def test_unauthorized_and_group_messages_never_reach_engine(self):
        bot = CafeTelegramBot(token='test-only', allowed_user_ids={42})
        with patch.object(bot, 'handle_message') as handle, patch.object(bot, 'send_message') as send:
            for user_id, chat_type in [(99, 'private'), (42, 'group'), (42, 'supergroup')]:
                self.assertFalse(bot.process_update({'message': {
                    'from': {'id': user_id}, 'chat': {'id': 1, 'type': chat_type}, 'text': 'ciro',
                }}))
            handle.assert_not_called()
            send.assert_not_called()

    def test_authorized_private_message_reaches_engine(self):
        bot = CafeTelegramBot(token='test-only', allowed_user_ids={42})
        with tempfile.TemporaryDirectory() as folder, \
             patch('app.ai.telegram_bot.LOG_FILE', Path(folder) / 'messages.log'), \
             patch.object(bot, 'handle_message', return_value='Rapor') as handle, \
             patch.object(bot, 'send_message', return_value=True) as send:
            self.assertTrue(bot.process_update({'message': {
                'from': {'id': 42}, 'chat': {'id': 42, 'type': 'private'}, 'text': 'ciro',
            }}))
            handle.assert_called_once_with('ciro')
            send.assert_called_once_with(42, 'Rapor')

    def test_exception_output_does_not_expose_token(self):
        bot = CafeTelegramBot(token='test-secret', allowed_user_ids={42})
        output = io.StringIO()
        with patch('app.ai.telegram_bot.requests.post', side_effect=OSError('URL test-secret')), \
             redirect_stdout(output):
            self.assertFalse(bot.send_message(42, 'Test'))
        self.assertNotIn('test-secret', output.getvalue())

    def test_unconfigured_allowlist_prevents_polling(self):
        bot = CafeTelegramBot(token='test-only', allowed_user_ids=set())
        with patch('app.ai.telegram_bot.requests.get') as request, redirect_stdout(io.StringIO()):
            bot.run_polling()
        request.assert_not_called()


if __name__ == '__main__':
    unittest.main()
