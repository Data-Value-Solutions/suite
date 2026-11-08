# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from suite.meet.utils import SUITE_USER_ROLE, assign_suite_role_to_all_users

HEALTHY = "suite-role-healthy@example.com"
BROKEN = "suite-role-broken@example.com"


class IntegrationTestAssignSuiteRole(IntegrationTestCase):
    def setUp(self) -> None:
        for email in (HEALTHY, BROKEN):
            if not frappe.db.exists("User", email):
                frappe.get_doc(
                    {
                        "doctype": "User",
                        "email": email,
                        "first_name": email.split("@")[0],
                        "send_welcome_email": 0,
                    }
                ).insert(ignore_permissions=True)
            frappe.db.delete("Has Role", {"parent": email, "role": SUITE_USER_ROLE})
            frappe.clear_cache(user=email)

        # Legacy data seen on real sites: the user's Contact holds its email twice, both primary.
        # Frappe's User.on_update re-saves that Contact, and Contact.validate rejects it.
        contact = frappe.db.get_value("Contact", {"user": BROKEN})
        if not contact:
            contact = (
                frappe.get_doc({"doctype": "Contact", "first_name": "suite-role-broken", "user": BROKEN})
                .insert(ignore_permissions=True)
                .name
            )
        frappe.db.delete("Contact Email", {"parent": contact})
        for idx in (1, 2):
            frappe.get_doc(
                {
                    "doctype": "Contact Email",
                    "parent": contact,
                    "parenttype": "Contact",
                    "parentfield": "email_ids",
                    "idx": idx,
                    "email_id": BROKEN,
                    "is_primary": 1,
                }
            ).db_insert()

    def test_a_user_that_cannot_be_saved_does_not_stop_the_others(self):
        failed = assign_suite_role_to_all_users()

        self.assertIn(BROKEN, failed)
        self.assertNotIn(HEALTHY, failed)
        self.assertIn(SUITE_USER_ROLE, frappe.get_roles(HEALTHY))
        self.assertNotIn(SUITE_USER_ROLE, frappe.get_roles(BROKEN))
