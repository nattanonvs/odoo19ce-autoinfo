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


class Website(models.Model):
    _inherit = "website"

    @api.model
    def od19_products(self):
        """Return the shared product catalog (see OD19_PRODUCT_CATALOG)."""
        return OD19_PRODUCT_CATALOG

    @api.model
    def od19_setup_website(self):
        """Brand the default website (idempotent)."""
        website = self.env.ref("website.default_website", raise_if_not_found=False)
        if not website or website.name != DEFAULT_NAME:
            return
        website.sudo().write({"name": WEBSITE_NAME})
        _logger.info("od19_website: renamed default website to %r", WEBSITE_NAME)
