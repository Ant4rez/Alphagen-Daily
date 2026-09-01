"""
Curated universe of AI-related US-listed tickers.

Organized by vertical for clarity and future extensibility.
Grouped constants let us test/screen specific verticals in isolation.
"""

# Hyperscalers + Big Tech AI
HYPERSCALERS = [
    "MSFT",   # Microsoft — Azure, Copilot, OpenAI stake
    "GOOGL",  # Alphabet — Gemini, DeepMind, GCP, TPUs
    "GOOG",   # Alphabet (class C)
    "AMZN",   # Amazon — AWS, Bedrock, Anthropic stake
    "META",   # Meta — Llama, Reality Labs
    "AAPL",   # Apple — Apple Intelligence
    "ORCL",   # Oracle — AI cloud infra, OpenAI partnership
    "IBM",    # IBM — Watson, hybrid AI
]

# Semiconductors & AI chips
SEMICONDUCTORS = [
    "NVDA",   # Nvidia — GPU leader
    "AMD",    # Advanced Micro Devices — Instinct MI300
    "INTC",   # Intel — Gaudi, foundry
    "TSM",    # Taiwan Semiconductor — foundry
    "AVGO",   # Broadcom — networking + custom ASIC
    "QCOM",   # Qualcomm — mobile AI
    "ARM",    # Arm Holdings — chip IP
    "SMCI",   # Super Micro — AI servers
    "MU",     # Micron — HBM memory
    "MRVL",   # Marvell — data center networking
    "LRCX",   # Lam Research — semi equipment
    "KLAC",   # KLA Corp — semi inspection
    "AMAT",   # Applied Materials — semi equipment
    "ASML",   # ASML — EUV lithography
    "COHR",   # Coherent — optics networking
]

# Cloud data platforms, observability, developer infra
DATA_PLATFORMS = [
    "SNOW",   # Snowflake — cloud data warehouse
    "MDB",    # MongoDB — NoSQL cloud
    "DDOG",   # Datadog — observability
    "NET",    # Cloudflare — edge + Workers AI
    "ESTC",   # Elastic — search + observability
    "CFLT",   # Confluent — Kafka managed
    "HCP",    # HashiCorp — infra as code
    "TEAM",   # Atlassian — collab + AI
]

# Enterprise AI SaaS
ENTERPRISE_AI = [
    "PLTR",   # Palantir — Foundry, AIP
    "AI",     # C3.ai — enterprise AI
    "CRM",    # Salesforce — Einstein
    "NOW",    # ServiceNow — Now Assist
    "ADBE",   # Adobe — Firefly, Sensei
    "INTU",   # Intuit — Intuit Assist
    "WDAY",   # Workday — AI HR
]

# Cybersecurity with AI
CYBERSECURITY = [
    "CRWD",   # CrowdStrike — Charlotte AI
    "ZS",     # Zscaler — SASE + AI
    "PANW",   # Palo Alto Networks
    "FTNT",   # Fortinet
    "S",      # SentinelOne — Purple AI
    "OKTA",   # Okta — identity + AI
]

# EDA / Chip design software
EDA = [
    "SNPS",   # Synopsys — EDA + AI chip design
    "CDNS",   # Cadence Design Systems
]

# Emerging / pure AI plays (higher volatility)
EMERGING_AI = [
    "BBAI",   # BigBear.ai — AI defense
    "SOUN",   # SoundHound — voice AI
    "PATH",   # UiPath — RPA + AI
    "APP",    # AppLovin — AI adtech
    "DUOL",   # Duolingo — AI language
    "RBLX",   # Roblox — AI-generated content
    "U",      # Unity — real-time 3D + AI
    "SMWB",   # Similarweb — data intelligence
]

# AI infrastructure (power, cooling, data center physical)
AI_INFRA_PHYSICAL = [
    "VRT",    # Vertiv — data center cooling/power
    "ETN",    # Eaton — power infrastructure
    "PWR",    # Quanta Services
    "HUBB",   # Hubbell — electrical infra
    "GEV",    # GE Vernova — power for data centers
]

# AI hardware / servers
AI_HARDWARE = [
    "DELL",   # Dell — AI servers
    "HPE",    # Hewlett Packard Enterprise — HPC
]

# Networking for AI workloads
NETWORKING = [
    "ANET",   # Arista Networks — data center networking
    "CIEN",   # Ciena — optical
    "CSCO",   # Cisco — networking
    "JNPR",   # Juniper Networks
]

# Quantum computing (frontier)
QUANTUM = [
    "IONQ",   # IonQ
    "QBTS",   # D-Wave Quantum
]

# AI consulting & integration
AI_CONSULTING = [
    "ACN",    # Accenture
]

# AI-heavy adjacencies (worth monitoring)
AI_ADJACENT = [
    "TSLA",   # Tesla — autonomy AI
    "SHOP",   # Shopify — AI commerce
    "UBER",   # Uber — autonomy + AI dispatch
    "NFLX",   # Netflix — recommendation AI
]

# International AI plays via ADRs (Europe / Asia listed in US)
INTERNATIONAL_ADR = [
    "BABA",   # Alibaba — China e-commerce + Alicloud + AI
    "BIDU",   # Baidu — China AI search + autonomous driving (Apollo)
    "JD",     # JD.com — China e-commerce + AI logistics
    "PDD",    # Pinduoduo/Temu — China AI-powered e-commerce
    "NTES",   # NetEase — China gaming + AI research
    "SE",     # Sea Ltd — Southeast Asia super-app (Shopee/Garena)
    "GRAB",   # Grab — Southeast Asia ride/delivery + AI
    "SONY",   # Sony — Japan semiconductors + robotics + entertainment
    "SAP",    # SAP — Germany enterprise software + AI (Joule)
    "SPOT",   # Spotify — Sweden recommendation AI
    "STLA",   # Stellantis — European auto tech + software
]

# Fintech using AI (payments, lending, banking)
FINTECH_AI = [
    "SOFI",   # SoFi — AI-driven consumer banking
    "AFRM",   # Affirm — AI credit / BNPL
    "HOOD",   # Robinhood — trading + AI research
    "UPST",   # Upstart — AI lending platform
    "COIN",   # Coinbase — crypto exchange
    "XYZ",    # Block (formerly Square) — AI merchant + Cash App
    "NU",     # Nubank — LatAm AI-first neobank
    "STNE",   # StoneCo — Brazil fintech
    "PAGS",   # PagSeguro — Brazil fintech
    "MELI",   # MercadoLibre — LatAm e-commerce + fintech + AI
]

# Robotics & industrial automation
ROBOTICS = [
    "ISRG",   # Intuitive Surgical — surgical robotics
    "TER",    # Teradyne — industrial robotics + semi test
    "IRBT",   # iRobot — consumer robotics
    "ROK",    # Rockwell Automation — industrial automation
    "EMR",    # Emerson Electric — automation + AI
    "SYM",    # Symbotic — warehouse automation
    "HON",    # Honeywell — industrial + robotics + AI
    "ABBNY",  # ABB — Swiss industrial automation (OTC ADR)
    "FANUY",  # Fanuc — Japan industrial robots (OTC ADR)
    "CGNX",   # Cognex — machine vision
]


# Full universe used by the screener (dedup applied)
AI_UNIVERSE: list[str] = sorted(set(
    HYPERSCALERS
    + SEMICONDUCTORS
    + DATA_PLATFORMS
    + ENTERPRISE_AI
    + CYBERSECURITY
    + EDA
    + EMERGING_AI
    + AI_INFRA_PHYSICAL
    + AI_HARDWARE
    + NETWORKING
    + QUANTUM
    + AI_CONSULTING
    + AI_ADJACENT
    + INTERNATIONAL_ADR
    + FINTECH_AI
    + ROBOTICS
))


def get_universe(verticals: list[str] | None = None) -> list[str]:
    """
    Return the ticker universe, optionally filtered to specific verticals.

    Args:
        verticals: optional list of vertical names (e.g. ["SEMICONDUCTORS", "ENTERPRISE_AI"]).
                   If None or empty, returns the full universe.

    Returns:
        Sorted deduplicated list of tickers.
    """
    if not verticals:
        return AI_UNIVERSE

    vertical_map = {
        "HYPERSCALERS": HYPERSCALERS,
        "SEMICONDUCTORS": SEMICONDUCTORS,
        "DATA_PLATFORMS": DATA_PLATFORMS,
        "ENTERPRISE_AI": ENTERPRISE_AI,
        "CYBERSECURITY": CYBERSECURITY,
        "EDA": EDA,
        "EMERGING_AI": EMERGING_AI,
        "AI_INFRA_PHYSICAL": AI_INFRA_PHYSICAL,
        "AI_HARDWARE": AI_HARDWARE,
        "NETWORKING": NETWORKING,
        "QUANTUM": QUANTUM,
        "AI_CONSULTING": AI_CONSULTING,
        "AI_ADJACENT": AI_ADJACENT,
        "INTERNATIONAL_ADR": INTERNATIONAL_ADR,
        "FINTECH_AI": FINTECH_AI,
        "ROBOTICS": ROBOTICS,
    }

    tickers: list[str] = []
    for v in verticals:
        key = v.upper()
        if key not in vertical_map:
            raise ValueError(f"Unknown vertical: {v}. Valid: {list(vertical_map.keys())}")
        tickers.extend(vertical_map[key])

    return sorted(set(tickers))


if __name__ == "__main__":
    print(f"Total universe: {len(AI_UNIVERSE)} tickers")
    print(f"Sample: {AI_UNIVERSE[:10]}")
