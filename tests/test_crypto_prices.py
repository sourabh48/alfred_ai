"""Crypto holdings follow CoinGecko's public prices (owner approved 2026-11-19). Synthetic data only; no network."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from apps.investments.models import Investment
from apps.investments.services import crypto_prices
from apps.investments.services.fund_prices import nav_state


class Reply:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def prices(age=timedelta(minutes=5), **coins):
    stamp = int((timezone.now() - age).timestamp())
    return Reply({coin: {**values, "last_updated_at": stamp} for coin, values in coins.items()})


class CryptoPriceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user("synthetic-coin-owner", password="pw-synthetic-1")
        self.coin = Investment.objects.create(user=self.user, asset_type="crypto", asset_name="Synthetic Bitcoin", currency="INR",
                                              invested_amount="1000.00", current_value="1000.00", coingecko_id="bitcoin", units="0.0125")

    def test_value_follows_the_price_and_only_coin_ids_and_currencies_leave(self):
        dollar = Investment.objects.create(user=self.user, asset_type="crypto", asset_name="Synthetic Ether", currency="USD",
                                           current_value="10.00", coingecko_id="ethereum", units="2")
        untouched = Investment.objects.create(user=self.user, asset_type="crypto", asset_name="No currency",
                                              current_value="5.00", coingecko_id="bitcoin", units="1")
        reply = prices(bitcoin={"inr": 8000000.5, "usd": 95000}, ethereum={"usd": 3100.25})
        with patch.object(crypto_prices.public_http, "request", return_value=reply) as sent:
            self.assertEqual(crypto_prices.refresh_crypto_values(), {"checked": 2, "updated": 2, "without_fresh_price": 0})
            self.assertEqual(crypto_prices.refresh_crypto_values()["updated"], 0)  # same price: nothing changes
        params = sent.call_args.kwargs["params"]
        self.assertEqual((params["ids"], params["vs_currencies"]), ("bitcoin,ethereum", "inr,usd"))
        self.assertNotIn("0.0125", str(sent.call_args))
        self.coin.refresh_from_db(); dollar.refresh_from_db(); untouched.refresh_from_db()
        self.assertEqual((self.coin.current_value, self.coin.nav), (Decimal("100000.01"), Decimal("8000000.5000")))  # 0.0125 x 8000000.5
        self.assertEqual(dollar.current_value, Decimal("6200.50"))
        self.assertEqual(untouched.current_value, Decimal("5.00"))
        self.assertEqual(nav_state(self.coin), "current")
        self.assertIsNone(self.coin.value_before_nav)  # Home's "funds revalued" note stays about funds

    def test_an_old_missing_or_failed_price_leaves_the_value_alone(self):
        for reply in (prices(age=timedelta(days=2), bitcoin={"inr": 1}), prices(ethereum={"inr": 1}), prices(bitcoin={"inr": 0.00001})):
            with patch.object(crypto_prices.public_http, "request", return_value=reply):
                self.assertEqual(crypto_prices.refresh_crypto_values()["without_fresh_price"], 1)
        with patch.object(crypto_prices.public_http, "request", side_effect=crypto_prices.public_http.PublicHTTPError("offline")):
            self.assertEqual(crypto_prices.refresh_crypto_values()["updated"], 0)
        self.coin.refresh_from_db()
        self.assertEqual((self.coin.current_value, self.coin.nav), (Decimal("1000.00"), None))
        self.assertEqual(nav_state(self.coin), "waiting")
        self.coin.nav_date = timezone.localdate() - timedelta(days=3)
        self.assertEqual(nav_state(self.coin), "stale")

    def test_search_picks_coins_by_name_and_the_form_saves_the_id(self):
        reply = Reply({"coins": [{"id": "bitcoin", "name": "Bitcoin", "symbol": "btc"}, {"id": "Bad Id!", "name": "x", "symbol": "x"}]})
        self.client.force_login(self.user)
        with patch.object(crypto_prices.public_http, "request", return_value=reply) as sent:
            found = self.client.get("/api/investments/coins/?q=bitc").json()["coins"]
            self.client.get("/api/investments/coins/?q=BITC")  # cached for a day
        self.assertEqual(found, [{"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC"}])
        self.assertEqual(sent.call_count, 1)
        bad = self.client.post("/api/investments/", {"asset_type": "crypto", "asset_name": "X", "invested_amount": "1",
                                                      "current_value": "1", "currency": "INR", "coingecko_id": "../x"})
        self.assertEqual(bad.status_code, 400)
        self.assertIn("coingecko_id", bad.json())

    def test_changing_the_coin_drops_the_old_price(self):
        self.coin.nav, self.coin.nav_date = Decimal("80000"), timezone.localdate()
        self.coin.save()
        self.client.force_login(self.user)
        self.client.patch(f"/api/investments/{self.coin.pk}/", {"coingecko_id": "ethereum"}, content_type="application/json")
        self.coin.refresh_from_db()
        self.assertEqual((self.coin.coingecko_id, self.coin.nav, self.coin.nav_date), ("ethereum", None, None))
