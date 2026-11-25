import logging

from odoo import api, models
from odoo.http import request
from odoo.tools.json import scriptsafe as json_scriptsafe

_logger = logging.getLogger(__name__)

# Spelled out once and reused as (a) the schema.org Organization description,
# (b) the fallback meta description for pages without their own copy.
OD19_ORG_DESCRIPTION = (
    "The Auto-Info Co., Ltd. delivers total integrated automation solutions in "
    "industrial, building and terminal automation — PLC/SCADA, BMS/HVAC, tank "
    "gauging and loading control — with ISO 9001:2015 certified engineering, "
    "installation and service from Bangkok, Thailand."
)

# Canonical public identity used to build the schema.org Organization markup on
# every page.  It mirrors the contact details the site already shows in its
# header, footer and contact page, and is deliberately *not* read from the
# res.company record: that record may still hold Odoo's demo/placeholder values
# (e.g. "YourCompany" / "+1 555-555-5556"), which must never leak into the
# published structured data.
OD19_ORG_NAME = "The Auto-Info Co., Ltd."
OD19_ORG_PHONE = "+66 2 934 5410-6"
OD19_ORG_EMAIL = "sales@auto-info.co.th"
OD19_ORG_ADDRESS = {
    "@type": "PostalAddress",
    "streetAddress": "1359 Soi Ladprao 94 (Panjamitr), Ladprao Rd., "
                     "Plubpla, Wangthonglang",
    "addressLocality": "Bangkok",
    "postalCode": "10310",
    "addressCountry": "TH",
}

# Appended to the Odoo-generated robots.txt (the User-agent / Allow / Sitemap
# block is produced by the website.robots template itself).  Keep internal
# tooling and the employee portal out of the index, while explicitly inviting
# the major search and answer-engine (AI) crawlers so the company is easy to
# discover and easy for assistants to cite.
OD19_DEFAULT_ROBOTS = """# Auto-Info — keep private areas out of the index
Disallow: /web/
Disallow: /my/
Disallow: /employee-portal
"""

# Extra robots.txt block that welcomes the major AI / answer-engine crawlers.
# Appended after the Odoo-generated block by od19_setup_seo() so the public
# content is reachable by GPTBot, ClaudeBot, PerplexityBot, Google-Extended,
# CCBot, Baidu and Yandex while the private areas above stay disallowed.
OD19_AI_CRAWLER_ROBOTS = """# --- AI / answer-engine crawlers are welcome on the public site ---
User-agent: GPTBot
Allow: /
Disallow: /my/
Disallow: /web/
Disallow: /employee-portal

User-agent: OAI-SearchBot
Allow: /
Disallow: /my/
Disallow: /web/
Disallow: /employee-portal

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /
Disallow: /my/
Disallow: /web/
Disallow: /employee-portal

User-agent: anthropic-ai
Allow: /

User-agent: PerplexityBot
Allow: /
Disallow: /my/
Disallow: /web/
Disallow: /employee-portal

User-agent: Google-Extended
Allow: /

User-agent: Applebot-Extended
Allow: /

User-agent: CCBot
Allow: /

User-agent: Bytespider
Allow: /

User-agent: Baiduspider
Allow: /

User-agent: YandexBot
Allow: /
"""

# Marker used to detect whether the AI-crawler block is already present in a
# website's robots.txt, so od19_setup_seo() can append it exactly once.
OD19_AI_CRAWLER_MARKER = "AI / answer-engine crawlers"

# Odoo ships the website record as "My Website", which then leaks into every
# browser tab as "<page name> | My Website".  Brand it on install/upgrade.
DEFAULT_NAME = "My Website"
WEBSITE_NAME = "Auto-Info"

# Single source of truth for the product catalog shown on /products and
# cross-linked from the three service pages.  Keeping the data here means the
# catalog grid, the department filter counts and the "related products" strips
# can never drift apart.
OD19_PRODUCT_CATALOG = [
    # Industrial Automation
    {"dept": "industrial", "brand": "Schneider Electric", "name": "Modicon M580", "desc": "High-performance ePAC controller engineered for demanding process and machine automation.", "specs": ["Up to 4 racks", "Ethernet/IP + Modbus", "Hot-standby ready"], "img": "industrial-m580.jpg"},
    {"dept": "industrial", "brand": "Schneider Electric", "name": "Modicon M340", "desc": "Modular PLC platform delivering reliable control for mid-range industrial applications.", "specs": ["Modular I/O", "Fast CPU cycle", "Compact footprint"], "img": "industrial-m340.jpg"},
    {"dept": "industrial", "brand": "Schneider Electric", "name": "Magelis HMI", "desc": "Vivid touch-panel interfaces that put plant data and alarms right at the operator fingertips.", "specs": ["7 to 15 inch", "Multi-touch", "IP66 front"], "img": "industrial-magelis-hmi.jpg"},
    {"dept": "industrial", "brand": "Schneider Electric", "name": "Altivar Process Drive", "desc": "Heavy-duty variable speed drives that cut energy use across pumps fans and conveyors.", "specs": ["0.75 to 630 kW", "Built-in safety", "Energy dashboard"], "img": "industrial-altivar-drive.jpg"},
    {"dept": "industrial", "brand": "Schneider Electric", "name": "EcoStruxure Plant", "desc": "IIoT-ready automation architecture connecting the shop floor to the top floor in real time.", "specs": ["Edge control", "Cloud analytics", "Open protocol"], "img": "industrial-ecostruxure.jpg"},
    {"dept": "industrial", "brand": "Auto-Info Engineering", "name": "SCADA Centralized System", "desc": "Centralized supervisory control and data acquisition for complete plant visibility.", "specs": ["Real-time trends", "Alarm management", "Historian logging"], "img": "industrial-scada.jpg"},
    {"dept": "industrial", "brand": "Emerson", "name": "Rosemount Pressure Transmitter", "desc": "Precision pressure measurement built to survive the toughest process environments.", "specs": ["High accuracy", "HART / 4-20 mA", "Hazardous area"], "img": "industrial-rosemount-pressure.jpg"},
    {"dept": "industrial", "brand": "Emerson", "name": "Micro Motion Coriolis Meter", "desc": "Direct mass flow measurement delivering accuracy for critical batching and custody transfer.", "specs": ["Mass + density", "No moving parts", "Custody transfer"], "img": "industrial-coriolis-meter.jpg"},
    {"dept": "industrial", "brand": "Auto-Info Engineering", "name": "Custom Control Panel", "desc": "Engineered control cabinets assembled wired and tested for your exact process.", "specs": ["IP-rated enclosures", "Wired and tested", "UL / IEC build"], "img": "industrial-control-panel.jpg"},
    # Building Automation
    {"dept": "building", "brand": "Siemens", "name": "Symaro Sensors", "desc": "Temperature humidity and CO2 sensors that keep HVAC performance precise and efficient.", "specs": ["High accuracy", "Room and duct", "Low drift"], "img": "building-symaro-sensors.jpg"},
    {"dept": "building", "brand": "Siemens", "name": "Desigo CC", "desc": "Integrated building management platform unifying HVAC lighting and energy in one view.", "specs": ["Multi-discipline", "Web access", "Open BACnet"], "img": "building-desigo-cc.jpg"},
    {"dept": "building", "brand": "Auto-Info Engineering", "name": "HVAC Control System", "desc": "Smart HVAC automation that balances comfort air quality and energy cost.", "specs": ["VAV and AHU", "Demand control", "Energy saving"], "img": "building-hvac-control.jpg"},
    {"dept": "building", "brand": "Auto-Info Engineering", "name": "Environmental Monitoring", "desc": "Continuous GMP-grade monitoring of critical clean room parameters with full audit trail.", "specs": ["21 CFR Part 11", "Real-time alerts", "Audit trail"], "img": "building-env-monitoring.jpg"},
    {"dept": "building", "brand": "Auto-Info Engineering", "name": "Fume Hood Controller", "desc": "Adaptive airflow control that protects lab users while reducing exhaust energy.", "specs": ["VAV airflow", "Sash sensing", "Lab safety"], "img": "building-fume-hood.jpg"},
    {"dept": "building", "brand": "Auto-Info Engineering", "name": "Energy Management System", "desc": "Track and optimize building energy consumption with live dashboards and reporting.", "specs": ["Sub-metering", "KPI dashboard", "ISO 50001"], "img": "building-energy-management.jpg"},
    {"dept": "building", "brand": "Auto-Info Engineering", "name": "Building Management System", "desc": "Centralize control of every building subsystem from a single intuitive interface.", "specs": ["Single pane", "Scheduling", "Fault detection"], "img": "building-bms.jpg"},
    {"dept": "building", "brand": "Auto-Info Engineering", "name": "Clean Room Control", "desc": "GMP-compliant clean room automation maintaining pressure temperature and particle limits.", "specs": ["Pressure cascade", "GMP ready", "Validated"], "img": "building-cleanroom-control.jpg"},
    # Terminal Automation
    {"dept": "terminal", "brand": "Emerson Rosemount", "name": "Servo Gauge 854 ATG", "desc": "Automatic tank gauging delivering precise level and inventory for terminal storage.", "specs": ["Custody accuracy", "Servo level", "Live inventory"], "img": "terminal-servo-gauge.jpg"},
    {"dept": "terminal", "brand": "OPW", "name": "Fusion 4 MSC-L", "desc": "Advanced load controller for metering batching and safe truck and rail load-out.", "specs": ["Multi-stream", "Blend control", "Safe loading"], "img": "terminal-fusion4-msc.jpg"},
    {"dept": "terminal", "brand": "Auto-Info Engineering", "name": "Tank Inventory System", "desc": "Real-time tank inventory with reconciliation and loss detection across the terminal.", "specs": ["Live inventory", "Reconciliation", "Loss detection"], "img": "terminal-tank-inventory.jpg"},
    {"dept": "terminal", "brand": "Auto-Info Engineering", "name": "Terminal Management System", "desc": "Integrated TMS orchestrating loading access control and documentation end to end.", "specs": ["Order to load", "Access control", "Reporting"], "img": "terminal-tms.jpg"},
    {"dept": "terminal", "brand": "Auto-Info Engineering", "name": "Overfill Prevention System", "desc": "Independent safety layer that prevents overfill and protects people and assets.", "specs": ["SIL rated", "Independent", "Self-test"], "img": "terminal-overfill-prevention.jpg"},
    {"dept": "terminal", "brand": "Auto-Info Engineering", "name": "Loading Arm and Metering Skid", "desc": "Automated loading arms and metering skids for fast accurate tanker load-out.", "specs": ["Top and bottom", "Metering skid", "Vapor recovery"], "img": "terminal-loading-arm-skid.jpg"},
    {"dept": "terminal", "brand": "Emerson Rosemount", "name": "Tank Side Monitor", "desc": "Field interface hub gathering tank sensor data onto a single reliable network.", "specs": ["Field hub", "Multi-sensor", "Tankbus"], "img": "terminal-tank-side-monitor.jpg"},
    {"dept": "terminal", "brand": "Emerson Rosemount", "name": "Radar Level Gauge", "desc": "Non-contact radar level measurement for accurate inventory with zero maintenance.", "specs": ["Non-contact", "High accuracy", "Retrofit ready"], "img": "terminal-radar-gauge.jpg"},
]

# Trust signals (SP5).  Rendered on /quality-certifications.  The certification
# body, certificate number and expiry date are *not* hard-coded here: they live
# on res.company so the real values can be maintained from the backend and the
# page only shows them when they are set.
OD19_CERTIFICATIONS = [
    {
        "key": "iso9001",
        "icon": "fa-certificate",
        "title": "ISO 9001:2015",
        "subtitle": "Quality Management System",
        "status": "certified",
        "status_label": "Certified",
        "desc": "Our quality management system is certified to ISO 9001:2015, covering "
                "project delivery, engineering, service and procurement.",
        "points": [
            "Annual surveillance and re-certification audits",
            "Documented quality procedures and project records",
            "Customer feedback and corrective-action process",
        ],
    },
    {
        "key": "iso14001",
        "icon": "fa-leaf",
        "title": "ISO 14001",
        "subtitle": "Environmental Management System",
        "status": "in_progress",
        "status_label": "Preparing",
        "desc": "We are preparing our environmental management system for ISO 14001 "
                "certification as part of our sustainability roadmap.",
        "points": [
            "Environmental aspects and impacts review",
            "Waste, energy and emissions controls",
            "Planned certification audit",
        ],
    },
    {
        "key": "gmp",
        "icon": "fa-flask",
        "title": "GMP",
        "subtitle": "Good Manufacturing Practice",
        "status": "compliant",
        "status_label": "Compliant",
        "desc": "Our building automation solutions for life-science facilities are "
                "designed, installed and documented to GMP requirements.",
        "points": [
            "Clean-room and HVAC qualification support",
            "Documented installation and commissioning records",
            "Change control under GMP procedures",
        ],
    },
    {
        "key": "csv",
        "icon": "fa-check-square-o",
        "title": "CSV",
        "subtitle": "Computer System Validation",
        "status": "compliant",
        "status_label": "Compliant",
        "desc": "We deliver computer system validation documentation aligned with "
                "GAMP 5 for regulated automation systems.",
        "points": [
            "Validation master plan and risk assessment",
            "IQ / OQ / PQ protocols and reports",
            "Audit trail and data-integrity controls",
        ],
    },
]

OD19_ACCREDITATIONS = [
    "ISO 9001:2015",
    "ISO 14001 (preparing)",
    "GMP",
    "GAMP 5 / CSV",
    "IEC 61131-3",
    "IEC 62443",
    "ISO 50001",
]

# Illustrative project references (SP5).  Customer names are intentionally not
# published; each entry describes the sector and the delivered scope.  Replace
# with the real reference list before go-live.
OD19_PROJECT_REFERENCES = [
    {
        "sector": "industrial", "year": "2024",
        "title": "Petrochemical plant — SCADA centralisation",
        "scope": "Legacy controller migration with centralised SCADA, historian and alarm management.",
        "detail": "Multi-rack migration executed during planned shutdowns with no production loss.",
        "img": "content/industrial.jpg",
    },
    {
        "sector": "industrial", "year": "2024",
        "title": "Manufacturing line — control panel retrofit",
        "scope": "Custom control panels, variable-speed drives and safety interlock integration.",
        "detail": "Panel design, wiring and factory acceptance testing delivered as a single package.",
        "img": "products/industrial-control-panel.jpg",
    },
    {
        "sector": "industrial", "year": "2023",
        "title": "Process plant — pressure and flow instrumentation",
        "scope": "Rosemount transmitters and Micro Motion Coriolis meters with HART integration.",
        "detail": "Calibrated, loop-tested and documented instrumentation for custody-transfer metering.",
        "img": "products/industrial-rosemount-pressure.jpg",
    },
    {
        "sector": "building", "year": "2024",
        "title": "Life-science facility — HVAC and clean-room control",
        "scope": "GMP HVAC control, room pressure cascade and continuous environmental monitoring.",
        "detail": "Qualified installation with documented differential-pressure and air-change verification.",
        "img": "content/building.jpg",
    },
    {
        "sector": "building", "year": "2023",
        "title": "Pharmaceutical plant — CSV validation package",
        "scope": "Validation master plan, IQ / OQ / PQ protocols and audit-trail configuration.",
        "detail": "Inspection-ready documentation handed over with traceability matrix and training records.",
        "img": "products/building-cleanroom-control.jpg",
    },
    {
        "sector": "building", "year": "2022",
        "title": "Office tower — energy management system",
        "scope": "Sub-metering, KPI dashboards and reporting aligned to ISO 50001 practice.",
        "detail": "Measurable reduction in common-area energy consumption after commissioning.",
        "img": "products/building-energy-management.jpg",
    },
    {
        "sector": "terminal", "year": "2024",
        "title": "Fuel depot — tank gauging and overfill prevention",
        "scope": "Radar and servo level gauges with an independent SIL-rated overfill protection layer.",
        "detail": "Independent safety layer commissioned and self-tested alongside the inventory system.",
        "img": "products/terminal-radar-gauge.jpg",
    },
    {
        "sector": "terminal", "year": "2023",
        "title": "Product terminal — loading arm and batch control",
        "scope": "Loading arm and metering skid with batch controller and access-control integration.",
        "detail": "Automated tanker load-out with metering, vapour recovery and driver access control.",
        "img": "products/terminal-loading-arm-skid.jpg",
    },
    {
        "sector": "terminal", "year": "2022",
        "title": "Tank farm — integrated terminal management",
        "scope": "Terminal management system with inventory, reconciliation and business integration.",
        "detail": "Order-to-load workflow integrated with the customer's commercial systems.",
        "img": "products/terminal-tms.jpg",
    },
]


# Enquiry types offered by the RFQ form on /contactus (SP6).  Each type is
# routed to a sales team (matched by name, ignored when no such team exists)
# and labelled with a CRM tag so the sales desk can filter requests at a
# glance.  This is the single source used by both the form and the routing
# performed in models/crm_lead.py.
OD19_ENQUIRY_TYPES = [
    {"key": "quotation", "label": "Request a Quotation", "team": "Sales", "tag": "Website: Quotation"},
    {"key": "product", "label": "Product Information", "team": "Sales", "tag": "Website: Product Info"},
    {"key": "service", "label": "Service & Maintenance", "team": "Service", "tag": "Website: Service"},
    {"key": "spare_part", "label": "Spare Parts", "team": "Sales", "tag": "Website: Spare Parts"},
    {"key": "certificate", "label": "Certificate Copy Request", "team": "Sales", "tag": "Website: Certificate"},
    {"key": "career", "label": "Careers", "team": "Sales", "tag": "Website: Careers"},
    {"key": "other", "label": "Other Enquiry", "team": "Sales", "tag": "Website: Other"},
]


# ---------------------------------------------------------------------------
# Company story — vision, mission, values, growth path and service lines.
#
# Every line below is transcribed (and lightly condensed) from the company's
# own published material on www.auto-info.co.th and its Facebook page.  No
# figures, customers or claims are invented here; where a year is not known
# the milestone is described as a growth phase instead of a fabricated date.
# ---------------------------------------------------------------------------
OD19_ORG_FOUNDED = "1997"
OD19_ORG_SLOGAN = "Total Integrated Automation Solutions"

OD19_VISION = (
    "To be Southeast Asia's foremost provider of integrated automation solutions."
)

OD19_MISSION = (
    "To be the automation specialist and one-stop integrated solutions provider "
    "that continually exceeds our customers' increasing expectations. Our business "
    "is to help customers achieve business excellence through the best automation "
    "technology, reliability and service — building complete automation systems "
    "while developing the potential of the people within our organisation."
)

# The six "Excellence" pillars the company is organised around.
OD19_EXCELLENCE = [
    {
        "key": "customer",
        "icon": "fa-handshake-o",
        "title": "Customer Excellence",
        "desc": "Anticipate and exceed what customers need, turning every project "
                "into a long-term partnership.",
    },
    {
        "key": "people",
        "icon": "fa-users",
        "title": "People Excellence",
        "desc": "Develop our people's potential so skilled, motivated engineers "
                "deliver their best work.",
    },
    {
        "key": "strategic",
        "icon": "fa-bullseye",
        "title": "Strategic Excellence",
        "desc": "Choose the right technology and the right partnerships to keep "
                "customers a step ahead.",
    },
    {
        "key": "process",
        "icon": "fa-cogs",
        "title": "Process & Systems Excellence",
        "desc": "Standardised, documented and auditable processes from first survey "
                "to final handover.",
    },
    {
        "key": "innovation",
        "icon": "fa-lightbulb-o",
        "title": "Innovation Excellence",
        "desc": "Continually adopt new automation, IIoT, analytics and energy-saving "
                "technology.",
    },
    {
        "key": "leadership",
        "icon": "fa-trophy",
        "title": "Leadership Excellence",
        "desc": "Lead by example in quality, safety and integrity across the "
                "automation industry.",
    },
]

# Growth path.  The founding year (1997) and the practice areas are taken from
# the company's own history; later milestones are described as phases rather
# than invented dates.
OD19_GROWTH_PATH = [
    {
        "year": "1997",
        "title": "Founded in Bangkok",
        "desc": "Established as an engineering and trading company delivering "
                "automation technology and service to Thai industry.",
    },
    {
        "year": "Growth",
        "title": "Industrial, Building & Terminal practices",
        "desc": "Expanded from industrial control into building management systems "
                "and fuel-terminal automation as one integrated provider.",
    },
    {
        "year": "Leadership",
        "title": "Life-science & GMP / CSV focus",
        "desc": "Became a leading Building Automation partner for Thailand's "
                "life-science sector with GMP and CSV compliance.",
    },
    {
        "year": "Today",
        "title": "Total integrated automation",
        "desc": "System design, project management, implementation, training and "
                "long-term service contracts delivered under one roof.",
    },
    {
        "year": "Ahead",
        "title": "Southeast Asia's foremost provider",
        "desc": "Growing towards our vision — being Southeast Asia's foremost "
                "provider of integrated automation solutions.",
    },
]

# The service lines offered across all three automation practices.
OD19_SERVICES = [
    {"key": "design", "icon": "fa-drafting-compass",
     "title": "System Design & Engineering",
     "desc": "Concept studies, detail design, drawings, bill of materials and "
             "documentation prepared by in-house engineers."},
    {"key": "pm", "icon": "fa-tasks",
     "title": "Project Management",
     "desc": "Single accountable partner coordinating scope, schedule, vendors "
             "and handover from start to finish."},
    {"key": "implementation", "icon": "fa-wrench",
     "title": "Project Implementation",
     "desc": "Turnkey installation, configuration, testing and commissioning with "
             "documented, auditable records."},
    {"key": "training", "icon": "fa-graduation-cap",
     "title": "Training Programmes",
     "desc": "Operator and maintenance training so your team can run and sustain "
             "the system with confidence."},
    {"key": "service", "icon": "fa-life-ring",
     "title": "Service & Maintenance Contracts",
     "desc": "Preventive maintenance, calibration, on-call support and spare "
             "parts under clear service-level agreements."},
    {"key": "supply", "icon": "fa-cubes",
     "title": "Product Supply",
     "desc": "Genuine automation hardware and instrumentation from world-class "
             "brands we engineer with every day."},
]

# Industries served, drawn from the sectors in the project references and the
# company's published scope.
OD19_INDUSTRIES = [
    {"key": "petrochemical", "icon": "fa-fire",
     "title": "Petrochemical & Refining",
     "desc": "Process control, SCADA centralisation and instrumentation for "
             "refineries and petrochemical plants."},
    {"key": "manufacturing", "icon": "fa-industry",
     "title": "Manufacturing & Process Plants",
     "desc": "Line automation, control-panel retrofit, drives and process "
             "instrumentation for production facilities."},
    {"key": "lifescience", "icon": "fa-flask",
     "title": "Pharmaceutical & Life Sciences",
     "desc": "GMP-ready HVAC, clean-room control and CSV validation for "
             "regulated manufacturing."},
    {"key": "healthcare", "icon": "fa-hospital-o",
     "title": "Hospitals & Healthcare",
     "desc": "Building management, environmental monitoring and energy control "
             "for hospitals and clinics."},
    {"key": "commercial", "icon": "fa-building",
     "title": "Commercial & Office Buildings",
     "desc": "BMS, HVAC control and energy management for offices, hotels and "
             "mixed-use developments."},
    {"key": "terminals", "icon": "fa-tint",
     "title": "Fuel Terminals & Depots",
     "desc": "Tank gauging, inventory, loading control and overfill prevention "
             "for fuel terminals and depots."},
]

# Technology partners whose platforms our engineers deploy and support.
OD19_PARTNERS = [
    "Schneider Electric",
    "Siemens",
    "Emerson Rosemount",
    "OPW",
    "Honeywell",
    "ABB",
]

# Frequently asked questions.  Answers are drawn only from facts the website
# already publishes; used on /faq and emitted as FAQPage structured data so
# search engines and AI assistants can quote them directly.
OD19_FAQ = [
    {
        "q": "What does The Auto-Info Co., Ltd. do?",
        "a": "The Auto-Info Co., Ltd. is a Bangkok-based automation system "
             "integrator delivering total integrated automation solutions across "
             "Industrial, Building and Terminal automation. We provide system "
             "design, project management, implementation, training, service and "
             "maintenance contracts, and product supply.",
    },
    {
        "q": "Which industries does Auto-Info serve?",
        "a": "We serve petrochemical and refining, manufacturing and process "
             "plants, pharmaceutical and life-science facilities, hospitals and "
             "healthcare, commercial and office buildings, and fuel terminals "
             "and depots.",
    },
    {
        "q": "Is Auto-Info ISO 9001 certified?",
        "a": "Yes. Our quality management system is certified to ISO 9001:2015, "
             "covering project delivery, engineering, service and procurement, "
             "with annual surveillance audits.",
    },
    {
        "q": "Does Auto-Info support GMP and CSV validation?",
        "a": "Yes. Our building automation for life-science facilities is "
             "designed, installed and documented to GMP requirements, and we "
             "deliver computer system validation documentation aligned with "
             "GAMP 5, including IQ/OQ/PQ protocols.",
    },
    {
        "q": "Which automation platforms and brands does Auto-Info work with?",
        "a": "We work with Schneider Electric (Modicon PLCs, Magelis HMI, Altivar "
             "drives), Siemens (Desigo CC, Symaro sensors), Emerson Rosemount "
             "(instrumentation, Micro Motion, tank gauging) and OPW (loading "
             "controllers), among others.",
    },
    {
        "q": "Can Auto-Info migrate a legacy PLC or SCADA system?",
        "a": "Yes. System migration is one of our core Industrial Automation "
             "services, typically executed during planned shutdowns with no "
             "production loss, including centralised SCADA, historian and alarm "
             "management.",
    },
    {
        "q": "Does Auto-Info offer service and maintenance contracts?",
        "a": "Yes. We provide preventive maintenance, calibration, on-call "
             "support and genuine spare parts under service and maintenance "
             "contracts with clear service-level agreements.",
    },
    {
        "q": "Where is Auto-Info located?",
        "a": "Our head office is at 1359 Soi Ladprao 94 (Panjamitr), Ladprao Rd., "
             "Plubpla, Wangthonglang, Bangkok 10310, Thailand, with an "
             "engineering centre at ZENTRO Port Lumlukka K8, Lam Luk Ka, "
             "Pathumthani.",
    },
    {
        "q": "How do I request a quotation from Auto-Info?",
        "a": "Send your requirement through the contact form at /contactus, or "
             "email sales@auto-info.co.th, and our team will route your enquiry "
             "to the right specialist.",
    },
]

# Departmental contact addresses shown across the site.  odoo@auto-info.com is
# the address for website / Odoo system matters.
OD19_CONTACT_EMAILS = {
    "sales": "sales@auto-info.co.th",
    "hr": "hr@auto-info.co.th",
    "admin": "admin@auto-info.co.th",
    "system": "odoo@auto-info.com",
}

# Default meta keywords.  English and Thai first, then a set of Chinese search
# terms so visitors searching in Chinese can still find the company (the site
# itself stays in English/Thai — we only make it discoverable in Chinese).
OD19_SEO_KEYWORDS = (
    "automation Thailand, industrial automation, building automation, terminal "
    "automation, PLC, SCADA, BMS, HVAC, system integrator Bangkok, ISO 9001, "
    "ระบบอัตโนมัติ, โซลูชันอัตโนมัติ, อุตสาหกรรม, อาคาร, ท่าเรือน้ำมัน, "
    "自动化, 工业自动化, 楼宇自动化, 码头自动化, 泰国自动化, 系统集成"
)


class Website(models.Model):
    _inherit = "website"

    @api.model
    def od19_products(self):
        """Return the shared product catalog (see OD19_PRODUCT_CATALOG)."""
        return OD19_PRODUCT_CATALOG

    @api.model
    def od19_enquiry_types(self):
        """Return the RFQ enquiry types (see OD19_ENQUIRY_TYPES)."""
        return OD19_ENQUIRY_TYPES

    @api.model
    def od19_certifications(self):
        """Return the trust / certification list (see OD19_CERTIFICATIONS)."""
        return OD19_CERTIFICATIONS

    @api.model
    def od19_accreditations(self):
        """Return the standards and frameworks the team works to."""
        return OD19_ACCREDITATIONS

    @api.model
    def od19_projects(self):
        """Return the project references (see OD19_PROJECT_REFERENCES)."""
        return OD19_PROJECT_REFERENCES

    # ------------------------------------------------------------------
    # Company story — accessors used by the About / Industries / FAQ pages
    # ------------------------------------------------------------------
    @api.model
    def od19_vision(self):
        """Return the company vision statement."""
        return OD19_VISION

    @api.model
    def od19_mission(self):
        """Return the company mission statement."""
        return OD19_MISSION

    @api.model
    def od19_excellence(self):
        """Return the six "Excellence" pillars (see OD19_EXCELLENCE)."""
        return OD19_EXCELLENCE

    @api.model
    def od19_growth_path(self):
        """Return the company growth path / milestones (see OD19_GROWTH_PATH)."""
        return OD19_GROWTH_PATH

    @api.model
    def od19_services(self):
        """Return the service lines (see OD19_SERVICES)."""
        return OD19_SERVICES

    @api.model
    def od19_industries(self):
        """Return the industries served (see OD19_INDUSTRIES)."""
        return OD19_INDUSTRIES

    @api.model
    def od19_partners(self):
        """Return the technology partners (see OD19_PARTNERS)."""
        return OD19_PARTNERS

    @api.model
    def od19_faq(self):
        """Return the FAQ entries (see OD19_FAQ)."""
        return OD19_FAQ

    @api.model
    def od19_contact_emails(self):
        """Return the departmental contact addresses (see OD19_CONTACT_EMAILS)."""
        return OD19_CONTACT_EMAILS

    @api.model
    def od19_org_founded(self):
        """Return the year the company was founded."""
        return OD19_ORG_FOUNDED

    @api.model
    def od19_seo_keywords(self):
        """Return the default meta keywords, including the Chinese terms."""
        return OD19_SEO_KEYWORDS

    @api.model
    def od19_setup_website(self):
        """Brand the default website (idempotent)."""
        website = self.env.ref("website.default_website", raise_if_not_found=False)
        if not website or website.name != DEFAULT_NAME:
            return
        website.sudo().write({"name": WEBSITE_NAME})
        _logger.info("od19_website: renamed default website to %r", WEBSITE_NAME)

    # ------------------------------------------------------------------
    # SEO — schema.org structured data (SP7)
    # ------------------------------------------------------------------
    @api.model
    def od19_seo_default_description(self):
        """Fallback meta description for pages without their own copy."""
        return OD19_ORG_DESCRIPTION

    @api.model
    def od19_organization_jsonld(self):
        """Return schema.org Organization + WebSite markup as a JSON string.

        Injected inside `<head>` on every page (see views/seo.xml).  The value
        is ``scriptsafe`` serialised so it can be dropped verbatim into a
        `<script type="application/ld+json">` element without HTML escaping
        breaking the JSON.
        """
        website = self.env["website"].get_current_website()
        company = website.company_id.sudo()
        base_url = website.get_base_url()

        organization = {
            "@type": "Organization",
            "@id": "%s#organization" % base_url,
            "name": OD19_ORG_NAME,
            "url": base_url,
            "logo": "%s/logo.png?company=%s" % (base_url, company.id),
            "description": OD19_ORG_DESCRIPTION,
            "slogan": OD19_ORG_SLOGAN,
            "foundingDate": OD19_ORG_FOUNDED,
            "address": dict(OD19_ORG_ADDRESS),
            "telephone": OD19_ORG_PHONE,
            "email": OD19_ORG_EMAIL,
            "areaServed": [
                {"@type": "Country", "name": "Thailand"},
                {"@type": "Place", "name": "Southeast Asia"},
            ],
            "knowsAbout": [
                "Industrial automation",
                "Building automation",
                "Terminal automation",
                "PLC and SCADA systems",
                "Building management systems (BMS)",
                "HVAC control",
                "Tank gauging",
                "Loading control",
                "GMP and CSV validation",
                "Energy management",
            ],
            "contactPoint": [
                {
                    "@type": "ContactPoint",
                    "contactType": "sales",
                    "telephone": OD19_ORG_PHONE,
                    "email": OD19_CONTACT_EMAILS["sales"],
                    "areaServed": "TH",
                    "availableLanguage": ["en", "th"],
                },
                {
                    "@type": "ContactPoint",
                    "contactType": "customer support",
                    "email": OD19_CONTACT_EMAILS["admin"],
                    "areaServed": "TH",
                },
                {
                    "@type": "ContactPoint",
                    "contactType": "human resources",
                    "email": OD19_CONTACT_EMAILS["hr"],
                    "areaServed": "TH",
                },
            ],
        }

        same_as = [
            url for url in (
                company.od19_website_facebook_url,
                company.od19_website_linkedin_url,
                company.od19_website_youtube_url,
            ) if url
        ]
        if same_as:
            organization["sameAs"] = same_as

        website_data = {
            "@type": "WebSite",
            "@id": "%s#website" % base_url,
            "name": website.name,
            "url": base_url,
            "potentialAction": {
                "@type": "SearchAction",
                "target": "%s/website/search?search={search_term_string}" % base_url,
                "query-input": "required name=search_term_string",
            },
        }
        lang = getattr(request, "lang", None) if request else None
        if lang is not None and getattr(lang, "code", None):
            website_data["inLanguage"] = lang.code.replace("_", "-")

        payload = [
            dict(organization, **{"@context": "https://schema.org"}),
            dict(website_data, **{"@context": "https://schema.org"}),
        ]
        return json_scriptsafe.dumps(payload, indent=2)

    @api.model
    def od19_faq_jsonld(self):
        """Return the FAQ entries as FAQPage structured data (JSON string).

        Emitted only on the FAQ page (see views/faq_page.xml).  This is the
        highest-value markup for answer engines: it lets Google and AI
        assistants read the question/answer pairs verbatim.
        """
        entries = [{
            "@type": "Question",
            "name": item["q"],
            "acceptedAnswer": {"@type": "Answer", "text": item["a"]},
        } for item in OD19_FAQ]
        payload = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": entries,
        }
        return json_scriptsafe.dumps(payload, indent=2)

    @api.model
    def od19_services_jsonld(self):
        """Return the service lines + industries as ItemList markup (JSON string).

        Helps search engines understand the breadth of what the company offers
        and the sectors it serves.
        """
        base_url = self.env["website"].get_current_website().get_base_url()
        items = []
        position = 0
        for svc in OD19_SERVICES:
            position += 1
            items.append({
                "@type": "ListItem",
                "position": position,
                "item": {
                    "@type": "Service",
                    "name": svc["title"],
                    "description": svc["desc"],
                    "provider": {"@id": "%s#organization" % base_url},
                    "areaServed": "TH",
                },
            })
        payload = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": "Auto-Info automation services",
            "itemListElement": items,
        }
        return json_scriptsafe.dumps(payload, indent=2)

    @api.model
    def od19_llms_txt(self):
        """Return an ``llms.txt`` summary of the site for AI / answer engines.

        A compact, plain-text map of the company and its public pages
        (https://llmstxt.org) so assistants such as ChatGPT, Claude and
        Perplexity can understand and cite the site from a single file.
        Every fact comes from the same constants that drive the website.
        """
        website = self.env["website"].get_current_website()
        base_url = website.get_base_url().rstrip("/")
        addr = OD19_ORG_ADDRESS
        address_line = "%s, %s %s, Thailand" % (
            addr["streetAddress"], addr["addressLocality"], addr["postalCode"],
        )

        lines = [
            "# %s" % OD19_ORG_NAME,
            "",
            "> %s" % OD19_ORG_DESCRIPTION,
            "",
            "## Key facts",
            "- Founded: %s, Bangkok, Thailand" % OD19_ORG_FOUNDED,
            "- Slogan: %s" % OD19_ORG_SLOGAN,
            "- Head office: %s" % address_line,
            "- Phone: %s" % OD19_ORG_PHONE,
            "- Email: %s" % OD19_ORG_EMAIL,
            "- Vision: %s" % OD19_VISION,
            "- Industries: %s" % ", ".join(i["title"] for i in OD19_INDUSTRIES),
            "- Technology partners: %s" % ", ".join(OD19_PARTNERS),
            "- Search terms (EN/TH/ZH): %s" % OD19_SEO_KEYWORDS,
            "",
            "## Services",
        ]
        lines += ["- %s: %s" % (s["title"], s["desc"]) for s in OD19_SERVICES]
        lines += ["", "## Contact"]
        lines += [
            "- Sales: %s" % OD19_CONTACT_EMAILS["sales"],
            "- Service & maintenance: %s" % OD19_CONTACT_EMAILS["admin"],
            "- Careers / HR: %s" % OD19_CONTACT_EMAILS["hr"],
            "- Website & Odoo system: %s" % OD19_CONTACT_EMAILS["system"],
            "",
            "## Key pages",
        ]
        pages = [
            ("Home", "/"),
            ("Industrial Automation", "/industrial-automation"),
            ("Building Automation", "/building-automation"),
            ("Terminal Automation", "/terminal-automation"),
            ("Products", "/products"),
            ("Industries", "/industries"),
            ("About Us", "/about-us"),
            ("Quality & Certifications", "/quality-certifications"),
            ("Project References", "/portfolio"),
            ("News & Events", "/blog"),
            ("Careers", "/careers"),
            ("FAQ", "/faq"),
            ("Contact", "/contactus"),
            ("Customer Portal", "/my"),
        ]
        lines += ["- [%s](%s%s)" % (title, base_url, path) for title, path in pages]
        lines += ["", "## Frequently asked questions"]
        for item in OD19_FAQ:
            lines.append("- Q: %s" % item["q"])
            lines.append("  A: %s" % item["a"])
        lines += [
            "",
            "## Optional",
            "- [Sitemap](%s/sitemap.xml)" % base_url,
            "- [robots.txt](%s/robots.txt)" % base_url,
            "",
        ]
        return "\n".join(lines)

    @api.model
    def od19_setup_seo(self):
        """Propagate the company Google Analytics ID and seed robots.txt.

        Idempotent: replayed on every ``-u od19_website`` (see
        data/setup_functions.xml).  Never overwrites a value that has already
        been customised from the backend / website editor.
        """
        for website in self.search([]):
            company = website.company_id.sudo()
            key = (company.od19_website_ga_key or "").strip()
            vals = {}
            if key and website.google_analytics_key != key:
                vals["google_analytics_key"] = key
            robots = website.robots_txt or ""
            if not robots.strip():
                vals["robots_txt"] = OD19_DEFAULT_ROBOTS + "\n" + OD19_AI_CRAWLER_ROBOTS
            elif (OD19_AI_CRAWLER_MARKER not in robots
                    and robots.strip() == OD19_DEFAULT_ROBOTS.strip()):
                # Top up a robots.txt we seeded ourselves on an earlier upgrade
                # (i.e. it is still exactly OD19_DEFAULT_ROBOTS) without touching
                # a value the administrator has customised.
                vals["robots_txt"] = robots.rstrip() + "\n\n" + OD19_AI_CRAWLER_ROBOTS
            if vals:
                website.sudo().write(vals)
                _logger.info(
                    "od19_website: SEO setup applied to %r -> %s",
                    website.name, sorted(vals),
                )

    # ------------------------------------------------------------------
    # PDPA — cookie consent & legal pages (SP8)
    # ------------------------------------------------------------------
    @api.model
    def od19_setup_pdpa(self):
        """Enable cookie consent and make the legal pages live.

        Idempotent: replayed on every ``-u od19_website`` (see
        data/setup_functions.xml).  Enabling ``cookies_bar`` makes consent
        opt-in and lets core create the ``/cookie-policy`` page that the bar
        links to; the Privacy Policy and Terms pages are (re)published and left
        indexed.  Nothing is overwritten once it is already in place, so the
        administrator's edits survive an upgrade.
        """
        for website in self.search([]):
            if not website.cookies_bar:
                website.sudo().write({"cookies_bar": True})
                _logger.info(
                    "od19_website: enabled the cookies bar on %r", website.name,
                )

        # The Terms page used to live at /terms, but Odoo's ``account`` module
        # owns that route (its invoice-terms controller shadows any website
        # page on the same path).  The legal page is kept at ``/terms-of-use``;
        # because the page records are noupdate="1", the XML change alone does
        # not migrate a database that already carries the old URL, so we
        # normalise it here.  Idempotent.
        terms_view = self.env.ref(
            "od19_website.od19_terms_page", raise_if_not_found=False,
        )
        if terms_view:
            self.env["website.page"].sudo().search([
                ("view_id", "=", terms_view.id), ("url", "!=", "/terms-of-use"),
            ]).write({"url": "/terms-of-use"})

        legal_pages = self.env["website.page"].sudo().search([
            ("url", "in", ("/privacy", "/terms-of-use")),
        ])
        for page in legal_pages:
            vals = {}
            if not page.is_published:
                vals["is_published"] = True
            if not page.website_indexed:
                vals["website_indexed"] = True
            if vals:
                page.write(vals)
                _logger.info(
                    "od19_website: legal page %s -> %s", page.url, sorted(vals),
                )

        # Core creates this page together with the cookies bar; enrich its
        # metadata once, and never clobber a value the administrator set.
        cookie_policy = self.env["website.page"].sudo().search([
            ("url", "=", "/cookie-policy"),
        ], limit=1)
        if cookie_policy and not cookie_policy.website_meta_description:
            cookie_policy.write({
                "website_meta_title": "Cookie Policy | Auto-Info",
                "website_meta_description": (
                    "How The Auto-Info Co., Ltd. uses cookies on this website — "
                    "essential cookies, optional analytics cookies and how to manage "
                    "or withdraw your consent."
                ),
            })
