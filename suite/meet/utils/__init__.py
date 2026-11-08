# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe

SUITE_USER_ROLE = "Suite User"


def after_app_install(app_name: str | None = None):
    assign_suite_role_to_all_users()


def assign_suite_role_to_all_users():
    """Give every enabled user the Suite User role.

    Each user is saved on its own savepoint. On an existing site one user can fail to save for
    reasons unrelated to Suite (Frappe's User.on_update re-saves the user's Contact, which fails on
    legacy data such as two primary email rows or a link to a deleted record). Such a user is
    skipped and logged instead of failing the whole install, which would otherwise leave the app
    half-installed. Returns the users that could not be updated."""

    if not frappe.db.exists("Role", SUITE_USER_ROLE):
        return []

    users = frappe.get_all(
        "User",
        filters={"enabled": 1, "name": ["not in", ["Guest", "Administrator"]]},
        pluck="name",
    )

    failed = []
    for user_name in users:
        user = frappe.get_doc("User", user_name)
        if any(r.role == SUITE_USER_ROLE for r in user.roles):
            continue

        user.append("roles", {"role": SUITE_USER_ROLE})
        frappe.db.savepoint("assign_suite_role")
        try:
            user.save(ignore_permissions=True)
        except Exception:
            frappe.db.rollback(save_point="assign_suite_role")
            frappe.clear_last_message()
            frappe.log_error(title=f"Suite: could not give {user_name} the {SUITE_USER_ROLE} role")
            failed.append(user_name)

    return failed
