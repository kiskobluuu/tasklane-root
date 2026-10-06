from __future__ import annotations

from .config import ASSET_URLS, CALCULATOR_URL, CONTEST_URL, PRODUCT_URL


def fallback_variants(channels: list[str]) -> list[dict]:
    variants = []
    if "facebook" in channels:
        slug = "safe_to_spend_problem"
        variants.append({
            "platform": "facebook",
            "angle": "bank_balance_is_not_spendable",
            "theme": "product_problem",
            "text": (
                "Your bank balance can be accurate and still be a bad spending number. "
                "Money for bills, goals and the days left before payday may already be spoken for.\n\n"
                "BetweenPay protects those amounts first and gives you one Safe-to-Spend number for the rest. "
                "It is $12.99 one time, with no subscription and no bank connection required.\n\n"
                "See how it works: " + PRODUCT_URL.format(source="facebook", content=slug)
            ),
            "title": None,
            "destination": PRODUCT_URL.format(source="facebook", content=slug),
            "asset_url": ASSET_URLS["product"],
            "source": "facebook", "medium": "organic",
            "campaign": "product_discovery", "content": slug,
            "hypothesis": "A clear problem/solution message should attract buyers who care more about the product than the contest.",
        })
    if "x" in channels:
        slug = "payday_formula"
        variants.append({
            "platform": "x",
            "angle": "payday_formula",
            "theme": "education",
            "text": (
                "A useful payday check:\n\nMoney now − bills before payday − protected goals − safety buffer "
                "= a clearer Safe-to-Spend number.\n\nBetweenPay turns that into a reusable planner for $12.99 once. "
                "No subscription.\n" + PRODUCT_URL.format(source="x", content=slug)
            ),
            "title": None,
            "destination": PRODUCT_URL.format(source="x", content=slug),
            "asset_url": ASSET_URLS["product"],
            "source": "x", "medium": "organic",
            "campaign": "product_discovery", "content": slug,
            "hypothesis": "Educational value may improve qualified clicks and purchase intent.",
        })
    if "pinterest" in channels:
        slug = "calculator_pin_autopilot"
        variants.append({
            "platform": "pinterest",
            "angle": "free_calculator",
            "theme": "calculator_problem",
            "title": "How Much Can I Safely Spend Until Payday?",
            "text": (
                "Your account balance is not always the same as your spending money. Protect bills, goals and a "
                "safety buffer first, then use the free BetweenPay Safe-to-Spend calculator to see what may actually "
                "be available until payday."
            ),
            "destination": CALCULATOR_URL.format(source="pinterest", content=slug),
            "asset_url": ASSET_URLS["calculator"],
            "source": "pinterest", "medium": "organic",
            "campaign": "visual_search", "content": slug,
            "hypothesis": "Search-intent calculator content can create low-friction traffic that later converts.",
        })
    return variants


def contest_variants(channels: list[str]) -> list[dict]:
    variants = []
    for platform in channels:
        slug = f"verified_challenge_{platform}"
        if platform == "pinterest":
            text = (
                "BetweenPay's live 30-day referral challenge has a $10,000 first-place cash prize and a $12,050 "
                "total Top-10 prize pool. The official page includes the live countdown, verified leaderboard and rules. "
                "BetweenPay itself is a $12.99 one-time Safe-to-Spend planner."
            )
            title = "BetweenPay $10,000 Referral Challenge — Official Live Page"
        else:
            text = (
                "The official BetweenPay $10,000 Referral Challenge is live. First place is $10,000 cash, the total "
                "Top-10 prize pool is $12,050, and the official page has the live countdown, verified leaderboard and rules.\n\n"
                "BetweenPay itself is a $12.99 one-time Safe-to-Spend planner. Eligible customers can choose to join "
                "the challenge after purchase.\n\n" + CONTEST_URL.format(source=platform, content=slug)
            )
            title = None
        variants.append({
            "platform": platform,
            "angle": "verified_leaderboard",
            "theme": "contest_credibility",
            "text": text,
            "title": title,
            "destination": CONTEST_URL.format(source=platform, content=slug),
            "asset_url": ASSET_URLS["contest"],
            "source": platform, "medium": "organic",
            "campaign": "live_10k", "content": slug,
            "hypothesis": "Legitimacy cues around the live rules and leaderboard may increase qualified attention without overpromising.",
        })
    return variants
