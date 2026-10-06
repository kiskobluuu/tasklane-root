from __future__ import annotations

APP_NAME = "BetweenPay Sales OS"
APP_VERSION = "1.0.1"
DEFAULT_WEEKLY_TARGET = 100
DEFAULT_PRODUCT_PRICE = 12.99
DEFAULT_ENGINE_INTERVAL_MINUTES = 30
DEFAULT_PUBLISH_INTERVAL_MINUTES = 10
DEFAULT_OPENAI_MODEL = "gpt-6-luna"
DEFAULT_DAILY_AI_CALL_LIMIT = 6
DEFAULT_DAILY_POST_CAP = 6
DEFAULT_EXPLORATION_SHARE = 0.30

BETWEENPAY_SITE = "https://betweenpay.tasklaneco.com"
CONTEST_URL = BETWEENPAY_SITE + "/contest.html?utm_source={source}&utm_medium=organic&utm_campaign=live_10k&utm_content={content}"
CALCULATOR_URL = BETWEENPAY_SITE + "/free-calculator.html?utm_source={source}&utm_medium=organic&utm_campaign=visual_search&utm_content={content}"
PRODUCT_URL = BETWEENPAY_SITE + "/?utm_source={source}&utm_medium=organic&utm_campaign=product_discovery&utm_content={content}"

SUPABASE_PROJECT_URL = "https://lvqnwnzuqcxpdryppmpm.supabase.co"
ASSET_BASE = SUPABASE_PROJECT_URL + "/functions/v1/betweenpay-social-assets"
ASSET_URLS = {
    "contest": ASSET_BASE + "?asset=contest",
    "product": ASSET_BASE + "?asset=product",
    "calculator": ASSET_BASE + "?asset=calculator",
}

COMPLETED_ORDER_STATUSES = {
    "completed", "captured", "paid", "fulfilled",
    "COMPLETED", "CAPTURED", "PAID", "FULFILLED",
}

PROTECTED_CHANGES = {
    "product_price", "contest_prizes", "official_rules", "refund_policy",
    "payment_configuration", "product_functionality", "paid_advertising",
}

CHANNELS = ("facebook", "x", "pinterest")
