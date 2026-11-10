import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

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

    @api.model
    def od19_setup_website(self):
        """Brand the default website (idempotent)."""
        website = self.env.ref("website.default_website", raise_if_not_found=False)
        if not website or website.name != DEFAULT_NAME:
            return
        website.sudo().write({"name": WEBSITE_NAME})
        _logger.info("od19_website: renamed default website to %r", WEBSITE_NAME)
