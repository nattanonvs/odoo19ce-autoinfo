# -*- coding: utf-8 -*-
"""Tests for the employee vehicle book (สมุดรถพนักงาน) - T11.

Covered: the most recently used vehicle is auto-filled on a new mileage
expense, the vehicle type/plate snapshot is copied, the last odometer
reading is offered as the trip's starting reading (the employee's own last
reading takes precedence over the vehicle book), creating or writing an
expense refreshes the vehicle's last-used date and last odometer, and the
record rule hides other employees' vehicles.
"""

from datetime import timedelta

from odoo import fields
from odoo.tests.common import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestVehicleBook(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.od19_mileage_rate = 5.0
        cls.employee = cls.env["hr.employee"].create({"name": "Driver One"})
        cls.product = cls.env["product.product"].create({
            "name": "Mileage Category (vehicle test)",
            "type": "service",
            "standard_price": 0.0,
            "can_be_expensed": True,
        })
        cls.old_vehicle = cls.env["od19.employee.vehicle"].create({
            "employee_id": cls.employee.id,
            "od19_plate_number": "OLD-1111",
            "od19_last_used_date": fields.Date.today() - timedelta(days=30),
        })
        cls.new_vehicle = cls.env["od19.employee.vehicle"].create({
            "employee_id": cls.employee.id,
            "od19_plate_number": "NEW-2222",
            "od19_last_used_date": fields.Date.today(),
        })

    def _mileage_form(self):
        form = Form(self.env["hr.expense"])
        form.name = "Mileage trip"
        form.employee_id = self.employee
        form.product_id = self.product
        form.payment_mode = "own_account"
        form.od19_is_mileage = True
        form.od19_mileage_distance_km = 10.0
        return form

    def test_latest_vehicle_is_auto_filled(self):
        with self._mileage_form() as form:
            expense = form.save()
        self.assertEqual(expense.od19_mileage_vehicle_id, self.new_vehicle)

    def test_vehicle_snapshot_copied(self):
        with self._mileage_form() as form:
            form.od19_mileage_vehicle_id = self.new_vehicle
            expense = form.save()
        self.assertEqual(expense.od19_mileage_plate, "NEW-2222")

    def test_create_updates_last_used_date(self):
        target = fields.Date.today() + timedelta(days=1)
        self.env["hr.expense"].create({
            "name": "Mileage trip",
            "employee_id": self.employee.id,
            "product_id": self.product.id,
            "payment_mode": "own_account",
            "od19_is_mileage": True,
            "od19_mileage_distance_km": 10.0,
            "od19_mileage_vehicle_id": self.new_vehicle.id,
            "od19_mileage_date": target,
            "quantity": 10.0,
            "total_amount": 50.0,
        })
        self.new_vehicle.invalidate_recordset()
        self.assertEqual(self.new_vehicle.od19_last_used_date, target)

    # ------------------------------------------------------------------
    # Latest odometer reading is offered as the next trip's start
    # ------------------------------------------------------------------
    def test_start_odometer_filled_from_vehicle_book(self):
        vehicle = self.env["od19.employee.vehicle"].create({
            "employee_id": self.employee.id,
            "od19_plate_number": "ODO-3333",
            "od19_last_used_date": fields.Date.today() + timedelta(days=1),
            "od19_last_odometer": 12345,
        })
        with self._mileage_form() as form:
            expense = form.save()
        self.assertEqual(expense.od19_mileage_vehicle_id, vehicle)
        self.assertEqual(expense.od19_mileage_odometer_start, 12345)

    def test_start_odometer_kept_when_already_set(self):
        self.env["od19.employee.vehicle"].create({
            "employee_id": self.employee.id,
            "od19_plate_number": "ODO-4444",
            "od19_last_used_date": fields.Date.today() + timedelta(days=2),
            "od19_last_odometer": 9999,
        })
        with self._mileage_form() as form:
            form.od19_mileage_odometer_start = 100
            expense = form.save()
        # The employee's own figure is never overwritten by the suggestion.
        self.assertEqual(expense.od19_mileage_odometer_start, 100)

    # ------------------------------------------------------------------
    # Last odometer is remembered on the employee (employee-first)
    # ------------------------------------------------------------------
    def test_end_odometer_remembered_on_employee(self):
        self.env["hr.expense"].create({
            "name": "Mileage trip",
            "employee_id": self.employee.id,
            "product_id": self.product.id,
            "payment_mode": "own_account",
            "od19_is_mileage": True,
            "od19_mileage_distance_km": 10.0,
            "od19_mileage_odometer_start": 1000,
            "od19_mileage_odometer_end": 2000,
            "quantity": 10.0,
            "total_amount": 50.0,
        })
        self.employee.invalidate_recordset()
        # Remembered even though the trip has no vehicle in the book.
        self.assertEqual(self.employee.od19_last_mileage_odometer, 2000)

    def test_employee_memory_precedes_vehicle_book(self):
        self.env["od19.employee.vehicle"].create({
            "employee_id": self.employee.id,
            "od19_plate_number": "ODO-5555",
            "od19_last_used_date": fields.Date.today() + timedelta(days=3),
            "od19_last_odometer": 55555,
        })
        self.employee.od19_last_mileage_odometer = 44444
        with self._mileage_form() as form:
            expense = form.save()
        self.assertEqual(
            expense.od19_mileage_vehicle_id.od19_plate_number, "ODO-5555")
        # The employee's own number wins over the vehicle book suggestion.
        self.assertEqual(expense.od19_mileage_odometer_start, 44444)

    def test_create_records_end_odometer_on_vehicle(self):
        self.env["hr.expense"].create({
            "name": "Mileage trip",
            "employee_id": self.employee.id,
            "product_id": self.product.id,
            "payment_mode": "own_account",
            "od19_is_mileage": True,
            "od19_mileage_distance_km": 10.0,
            "od19_mileage_vehicle_id": self.new_vehicle.id,
            "od19_mileage_odometer_start": 1000,
            "od19_mileage_odometer_end": 1500,
            "quantity": 10.0,
            "total_amount": 50.0,
        })
        self.new_vehicle.invalidate_recordset()
        self.assertEqual(self.new_vehicle.od19_last_odometer, 1500)

    def test_write_records_end_odometer_on_vehicle(self):
        expense = self.env["hr.expense"].create({
            "name": "Mileage trip",
            "employee_id": self.employee.id,
            "product_id": self.product.id,
            "payment_mode": "own_account",
            "od19_is_mileage": True,
            "od19_mileage_distance_km": 10.0,
            "od19_mileage_vehicle_id": self.new_vehicle.id,
            "od19_mileage_odometer_start": 1000,
            "quantity": 10.0,
            "total_amount": 50.0,
        })
        self.new_vehicle.invalidate_recordset()
        self.assertEqual(self.new_vehicle.od19_last_odometer, 0)
        expense.write({"od19_mileage_odometer_end": 2200})
        self.new_vehicle.invalidate_recordset()
        self.assertEqual(self.new_vehicle.od19_last_odometer, 2200)

    def test_other_employee_cannot_see_my_vehicles(self):
        other_user = self.env["res.users"].create({
            "name": "Other Driver",
            "login": "od19_vehicle_other",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        other_employee = self.env["hr.employee"].create({
            "name": "Driver Two",
            "user_id": other_user.id,
        })
        other_vehicle = self.env["od19.employee.vehicle"].create({
            "employee_id": other_employee.id,
            "od19_plate_number": "OTHER-9999",
        })
        visible = self.env["od19.employee.vehicle"].with_user(
            other_user).search([])
        self.assertNotIn(self.new_vehicle, visible)
        self.assertIn(other_vehicle, visible)
