import re

filepath = r"d:\Soft\UTCAP\V0040\ut_vfx\gui\components\main_window_builder.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# We want to insert `add_category_header` in specific places.

# 1. PRODUCTION
content = content.replace(
    '            # Home Tab (Cinematic Hub)',
    '            self.tab_coordinator.add_category_header("PRODUCTION")\n\n            # Home Tab (Cinematic Hub)'
)

# 2. Add Prod Tabs after Dashboard Pro
prod_tabs = """

            # Production Scheduling
            self.tab_coordinator.register_tab_factory(
                "Scheduling",
                lambda: ProdSchedulingTab(),
                icon="📅",
                permission_key="Scheduling",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs,
                tooltip="Production Scheduling & Gantt Charts"
            )

            # Production Bidding
            self.tab_coordinator.register_tab_factory(
                "Bidding",
                lambda: ProdBiddingTab(),
                icon="💰",
                permission_key="Bidding",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs,
                tooltip="Project Bidding & Cost Tracking"
            )
"""
content = content.replace(
    '            # Settings\n            def create_settings():',
    f'{prod_tabs}\n            # Settings\n            def create_settings():'
)

# 3. Move Attendance and HRMS tabs to the right spot. Actually Attendance is currently defined near the bottom. Let's just insert HRMS header and new tabs right before Attendance.
hrms_tabs = """
            self.tab_coordinator.add_category_header("HRMS")

            # Leave Management
            self.tab_coordinator.register_tab_factory(
                "Leave Management",
                lambda: HrmsLeaveTab(),
                icon="🌴",
                permission_key="HRMS",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs,
                tooltip="Manage Paid Time Off and Leaves"
            )

            # Payroll & Compensation
            self.tab_coordinator.register_tab_factory(
                "Payroll",
                lambda: HrmsPayrollTab(),
                icon="💸",
                permission_key="HRMS",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs,
                tooltip="Payroll generation and compensation"
            )

            # Onboarding
            self.tab_coordinator.register_tab_factory(
                "Onboarding",
                lambda: HrmsOnboardingTab(),
                icon="🤝",
                permission_key="HRMS",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs,
                tooltip="Employee Onboarding Workflows"
            )

            # Performance
            self.tab_coordinator.register_tab_factory(
                "Performance",
                lambda: HrmsPerformanceTab(),
                icon="📈",
                permission_key="HRMS",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs,
                tooltip="Artist Performance and Reviews"
            )
"""
content = content.replace(
    '            # Attendance\n            self.tab_coordinator.register_tab_factory(\n                "Attendance",',
    f'{hrms_tabs}\n            # Attendance\n            self.tab_coordinator.register_tab_factory(\n                "Attendance",'
)


it_tabs = """
            self.tab_coordinator.add_category_header("IT & INFRA")

            # Hardware Inventory
            self.tab_coordinator.register_tab_factory(
                "Hardware",
                lambda: ItInventoryTab(),
                icon="🖥️",
                permission_key="IT",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs,
                tooltip="Studio Hardware Inventory"
            )

            # Software Licenses
            self.tab_coordinator.register_tab_factory(
                "Licenses",
                lambda: ItLicensesTab(),
                icon="🔑",
                permission_key="IT",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs,
                tooltip="DCC Software Licenses Tracking"
            )

            # IT Ticketing
            self.tab_coordinator.register_tab_factory(
                "Ticketing",
                lambda: ItTicketingTab(),
                icon="🎫",
                permission_key=None,
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs,
                tooltip="Submit and track IT Helpdesk tickets"
            )

            # Auto Deployment
            self.tab_coordinator.register_tab_factory(
                "Deployment",
                lambda: ItDeploymentTab(),
                icon="📦",
                permission_key="IT",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs,
                tooltip="Manage automated script and software deployments"
            )

            self.tab_coordinator.add_category_header("SYSTEM")
"""
content = content.replace(
    '            # Admin Panel\n            self.tab_coordinator.register_tab_factory(\n                "Admin Panel",',
    f'{it_tabs}\n            # Admin Panel\n            self.tab_coordinator.register_tab_factory(\n                "Admin Panel",'
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated main_window_builder.py")
