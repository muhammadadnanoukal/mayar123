from odoo import models, fields, api
import pytz
from pytz import timezone, utc
import base64
import xlrd
from odoo.exceptions import UserError
import datetime
from xlrd.xldate import xldate_as_datetime
from datetime import timedelta


class ApprovalCategory(models.Model):
    _inherit = 'approval.category'
    overTime = fields.Many2one('hr.work.entry.type')
    Late = fields.Many2one('hr.work.entry.type')
    atten = fields.Many2one('hr.work.entry.type')


class ExcelData(models.Model):
    _name = 'excel.data'
    _description = 'Excel Data'

    approval_request_id = fields.Many2one('approval.request')
    employee = fields.Char(string='Employee', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    start_hour = fields.Float(string='Start Hour', readonly=True)
    worked_hours = fields.Float(string='Worked Hours', readonly=True)
    late = fields.Float(string='Late')
    overtime = fields.Float(string='Overtime')
    apporvlelateee = fields.Boolean(default=True, string='Approval Late')
    apporvleovertime = fields.Boolean(default=True, string='Approval OverTime')


class EmployeesAttendanceReportWizard(models.TransientModel):
    _name = 'work.entry.inh.wizard'

    excel_file = fields.Binary(string='Excel File', required=True)
    approver_ids = fields.Many2many('res.users', string="Approvers", required=True)

    def import_excel_data(self):

        excel_data = self.excel_file
        print('excel_data..', excel_data)
        # user_ids = self.approver_ids.mapped('id')
        # print('user_ids==>', user_ids)

        # *********************************************#
        workbook = xlrd.open_workbook(file_contents=base64.b64decode(excel_data))
        print('workbook..', workbook)

        # Get the first sheet by index (assuming it's the first sheet)
        sheet = workbook.sheet_by_index(0)
        print('sheet..', sheet)
        # Get column names from the first row
        column_names = [cell.value for cell in sheet.row(0)]
        print('column_names..', column_names)
        # Check if all required columns are present
        required_columns = ['employee', 'date', 'start_hour', 'worked_hours', 'late', 'overtime']

        approval_category = self.env['approval.category'].search([('name', '=', 'work entry')], limit=1)
        # Create the approval request
        approval_request = self.env['approval.request'].sudo().create({
            'name': 'New Approval Request',
            'category_id': approval_category.id,
            'attachment': excel_data,
            'request_owner_id': self.env.user.id
        })
        print('approval_request..', approval_request)

        if not all(column in column_names for column in required_columns):
            raise UserError("The Excel file does not contain all the required columns.")
        # Iterate through the rows starting from the second row
        for row_index in range(1, sheet.nrows):
            row = sheet.row_values(row_index)
            # Extract the data from each column based on the column names
            employee = row[0]
            date = row[1]
            dt = datetime.datetime(*xlrd.xldate.xldate_as_tuple(row[1], workbook.datemode))
            start_hour = row[2]
            worked_hours = row[3]
            late = row[4]
            overtime = row[5]

            gcc = self.env['excel.data'].sudo().create({
                'approval_request_id': approval_request.id,
                'employee': employee,
                'date': dt,
                'start_hour': start_hour,
                'worked_hours': worked_hours,
                'late': late,
                'overtime': overtime,
                'apporvlelateee': 'True',
                'apporvleovertime': 'True',
            })

            # TODO: Create a work entry using the extracted data

        # Print the data
        print('Row Data:', employee, date, start_hour, worked_hours, late, overtime)
        # *********************************************#

        # Create work entries using the extracted data


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'
    excel_data_ids = fields.One2many('excel.data', 'approval_request_id', string='Excel Data')

    def action_approve(self, approver=None):
        if self.category_id.atten and self.category_id.Late and self.category_id.overTime:
            super(ApprovalRequest, self).action_approve(approver=approver)

            for excel_data in self.excel_data_ids:
                employee = excel_data.employee
                date = excel_data.date
                dt = date  # Assuming dt field in excel.data is already a datetime value
                start_hour = excel_data.start_hour
                worked_hours = excel_data.worked_hours
                late = excel_data.late
                overtime = excel_data.overtime
                oprolate = excel_data.apporvlelateee
                oproovertime = excel_data.apporvleovertime

                if not oprolate:
                    late = 0

                if not oproovertime:
                    overtime = 0

                mm = self.category_id.atten
                print('Row Data:', dt, employee, date, start_hour, worked_hours, late, overtime)
                # Convert date_value to a datetime object
                date_start = datetime.datetime.combine(date, datetime.time(hour=5, minute=0, second=0))

                date_stop = date_start.replace(hour=14, minute=0, second=0)

                # Set the timezone to UTC
                timezone = pytz.timezone('UTC')

                # Convert datetime values to timezone-aware datetime
                date_start_timezone = timezone.localize(date_start)
                date_stop_timezone = timezone.localize(date_stop)

                # Convert timezone-aware datetime to UTC naive datetime
                date_start_naive = date_start_timezone.astimezone(pytz.UTC).replace(tzinfo=None)
                date_stop_naive = date_stop_timezone.astimezone(pytz.UTC).replace(tzinfo=None)
                print('00000000=>',employee.split('.')[0])
                existing_work_entries = self.env['hr.work.entry'].search([
                    ('employee_id', '=',
                     self.env['hr.employee'].search(['|', ('name', '=', employee), ('registration_number', '=', employee.split('.')[0])],
                                                    limit=1).id),
                    ('date_start', '>=', date_start_naive.replace(hour=0, minute=0, second=0)),
                    ('date_stop', '<=', date_start_naive.replace(hour=23, minute=59, second=59)),
                ])
                print('existing_work_entries...', existing_work_entries)
                # Delete existing work entries
                existing_work_entries.unlink()
                print('after delete existing_work_entries...', existing_work_entries)
                dd = self.category_id.Late
                # # Check if there is a delay value
                if late:
                    late_hours = float(late)
                    if late_hours > 0:
                        late_start = date_start_naive
                        late_stop = late_start + timedelta(hours=late_hours)
                        late_work_entry_type_id = self.env['hr.work.entry.type'].search([('code', '=', 'DELAY')]).id
                        print('asdasdasd==>', type(employee))
                        res = ""
                        for c in employee:
                            if c != ".":
                                res += c
                            else:
                                break
                        print(' res ', res)
                        employee_domain = ['|', ('name', '=', employee),
                                           ('registration_number', '=', res)]
                        employee_record = self.env['hr.employee'].search(employee_domain, limit=1)
                        print(' employee_domain..==>', employee_domain)
                        print('employee_record..==>', employee_record)
                        late_work_entry = self.env['hr.work.entry'].create({
                            'name': 'late',
                            'employee_id': employee_record.id,
                            'work_entry_type_id': dd.id,
                            'date_start': late_start,
                            'date_stop': late_stop,
                        })

                        date_start_naive = late_stop  # Update the start time to be after the delay
                res = ""
                for c in employee:
                    if c != ".":
                        res += c
                    else:
                        break
                print(' res ', res)
                employee_domain = ['|', ('name', '=', employee), ('registration_number', '=', res)]
                employee_record = self.env['hr.employee'].search(employee_domain, limit=1)
                print('2employee_domain..==>', employee_domain)
                print('2employee_record..==>', employee_record)
                work_entry = self.env['hr.work.entry'].create({
                    'name': 'attendance',
                    'employee_id': employee_record.id,
                    'work_entry_type_id': mm.id,
                    'date_start': date_start_naive,
                    'date_stop': date_stop_naive,
                })
                # Check if overtime has a value
                cc = self.category_id.overTime
                res = ""
                for c in employee:
                    if c != ".":
                        res += c
                    else:
                        break

                print('cccc==>', cc)
                if overtime:
                    overtime_hours = float(overtime)
                    if overtime_hours > 0:
                        overtime_start = date_stop_naive
                        overtime_stop = overtime_start + timedelta(
                            hours=overtime_hours)  # Assuming overtime duration is 8 hours
                        employee_domain = ['|', ('name', '=', employee),
                                           ('registration_number', '=', res)]
                        employee_record = self.env['hr.employee'].search(employee_domain, limit=1)
                        print('3employee_domain..==>', employee_domain)
                        print('3employee_record..==>', employee_record)
                        overtime_work_entry = self.env['hr.work.entry'].create({
                            'name': 'Overtime',
                            'employee_id': employee_record.id,
                            'work_entry_type_id': cc.id,
                            'date_start': overtime_start,
                            'date_stop': overtime_stop,
                        })
        else:
            raise UserError("please chose work entry type from approval type")
