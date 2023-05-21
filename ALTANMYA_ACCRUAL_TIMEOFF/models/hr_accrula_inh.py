from odoo import api, fields, models
import logging
import pytz
import math
from odoo.tools.date_utils import get_timedelta


from collections import namedtuple, defaultdict
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from datetime import datetime, timedelta, time
from pytz import timezone, UTC
from odoo.tools import date_utils

from odoo import api, Command, fields, models, tools
from odoo.addons.base.models.res_partner import _tz_get
from odoo.addons.resource.models.resource import float_to_time, HOURS_PER_DAY
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare, format_date
from odoo.tools.float_utils import float_round
from odoo.tools.misc import format_date
from odoo.tools.translate import _
from odoo.osv import expression

_logger = logging.getLogger(__name__)

DAYS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
# Used for displaying the days and reversing selection -> integer
DAY_SELECT_VALUES = [str(i) for i in range(1, 29)] + ['last']
DAY_SELECT_SELECTION_NO_LAST = tuple(zip(DAY_SELECT_VALUES, (str(i) for i in range(1, 29))))


class HrLeaveInh(models.Model):
    _inherit = 'hr.leave'
    # accrual_plan_id = fields.Many2one('hr.leave.accrual.plan', string='Accrual Plan')
    possible_days = fields.Char('Forecast Future Allocation', readonly=True, compute='_get_date_possible')

    @api.depends('request_date_from', 'holiday_status_id')
    # @api.onchange('request_date_from')
    def _get_date_possible(self):
        for holiday in self:
            if holiday.holiday_status_id:
                holiday.possible_days = ""
                aco_hr_leave = holiday.holiday_status_id.Forecast_Future_Allocation

                print('b6e55 mbsmr..', holiday.holiday_status_id.Forecast_Future_Allocation)
                if aco_hr_leave:
                    # Perform the necessary computations
                    mapped_days = self.holiday_status_id.get_employees_days(
                        (holiday.employee_id | holiday.employee_ids).ids,
                        holiday.date_from.date())
                    if holiday.holiday_type != 'employee' \
                            or not holiday.employee_id and not holiday.employee_ids \
                            or holiday.holiday_status_id.requires_allocation == 'no':
                        continue
                        print('holiday.employee_id.outsiad..',holiday.employee_id)
                    if holiday.employee_id:
                        print('holiday.employee_id.insiad..', holiday.employee_id)
                        leave_days = mapped_days[holiday.employee_id.id][holiday.holiday_status_id.id]
                        allocation = self.env['hr.leave.allocation'].search([('employee_id', '=', holiday.employee_id.id),
                                                                             ('allocation_type', '=', 'accrual')])
                        m = allocation.get_total_invoked(holiday.request_date_from)

                        holiday.possible_days = m + leave_days['virtual_remaining_leaves']
                        print('self.possible_days..', holiday.possible_days)
                        print("leave_days['virtual_remaining_leaves']", leave_days['virtual_remaining_leaves'])
                        print('mvvv.m..', m)
                else:
                    # Set possible_days to a default value when Forecast_Future_Allocation is False
                    mapped_days = self.holiday_status_id.get_employees_days(
                        (holiday.employee_id | holiday.employee_ids).ids,
                        holiday.date_from.date())
                    if holiday.holiday_type != 'employee' \
                            or not holiday.employee_id and not holiday.employee_ids \
                            or holiday.holiday_status_id.requires_allocation == 'no':
                        continue
                    print('holiday.employee_id.outsiad2..', holiday.employee_id)
                    if holiday.employee_id:
                        print('holiday.employee_id.outsiad33..', holiday.employee_id, mapped_days)
                        leave_days = mapped_days[holiday.employee_id.id][holiday.holiday_status_id.id]
                        print('leave_daysasd..', leave_days)
                        allocation = self.env['hr.leave.allocation'].search([('employee_id', '=', holiday.employee_id.id),
                                                                             ('allocation_type', '=', 'accrual')])
                        m = allocation.get_total_invoked(holiday.request_date_from)

                        holiday.possible_days = leave_days['virtual_remaining_leaves']
                        print('self.possible_days..', holiday.possible_days)
                        print("leave_days['virtual_remaining_leaves']", leave_days['virtual_remaining_leaves'])
                        print('mvvv.m..', m)
            else:
                holiday.possible_days = ""

    @api.constrains('state', 'number_of_days', 'holiday_status_id')
    def _check_holidays(self):
        for holiday in self:


            print('b6e55 mbsmr..', holiday.holiday_status_id.Forecast_Future_Allocation)
            aco_hr_leave = holiday.holiday_status_id.Forecast_Future_Allocation

            mapped_days = self.holiday_status_id.get_employees_days((holiday.employee_id | holiday.employee_ids).ids,
                                                                    holiday.date_from.date())
            if holiday.holiday_type != 'employee' \
                    or not holiday.employee_id and not holiday.employee_ids \
                    or holiday.holiday_status_id.requires_allocation == 'no':
                continue
            if holiday.employee_id:
                leave_days = mapped_days[holiday.employee_id.id][holiday.holiday_status_id.id]
                allocation = self.env['hr.leave.allocation'].search([('employee_id', '=', holiday.employee_id.id),
                                                                     ('allocation_type', '=', 'accrual')])
                m = allocation.get_total_invoked(holiday.request_date_from)
                print('tetetst..', m)
                print('leave_days..',leave_days)

                if aco_hr_leave:
                    print('test-2..')
                    if float_compare(leave_days['remaining_leaves'], 0, precision_digits=2) == -1 \
                            or float_compare(leave_days['virtual_remaining_leaves'] + m, 0, precision_digits=2) == -1:
                        print('test_inside_1...',leave_days['virtual_remaining_leaves'] + m)
                        raise ValidationError(
                            _('The number of remaining time off is not sufficient for this time off type.\n'
                              'Please also check the time off waiting for validation.'))
                else:
                    print('test-3..')
                    if float_compare(leave_days['remaining_leaves'], 0, precision_digits=2) == -1 \
                            or float_compare(leave_days['virtual_remaining_leaves'], 0, precision_digits=2) == -1:
                        print('test_inside_2...', leave_days['virtual_remaining_leaves'])
                        raise ValidationError(
                            _('The number of remaining time off is not sufficient for this time off type.\n'
                              'Please also check the time off waiting for validation.'))

            else:
                unallocated_employees = []
                for employee in holiday.employee_ids:
                    leave_days = mapped_days[employee.id][holiday.holiday_status_id.id]
                    if float_compare(leave_days['remaining_leaves'], self.number_of_days, precision_digits=2) == -1 \
                            or float_compare(leave_days['virtual_remaining_leaves'], self.number_of_days,
                                             precision_digits=2) == -1:
                        unallocated_employees.append(employee.name)
                if unallocated_employees:
                    raise ValidationError(
                        _('The number of remaining time off is not sufficient for this time off type.\n'
                          'Please also check the time off waiting for validation.')
                        + _('\nThe employees that lack allocation days are:\n%s',
                            (', '.join(unallocated_employees))))


class test(models.Model):
    _inherit = 'hr.leave.allocation'

    def get_total_invoked(self, leave_start_date):
        forcasted_days = 0
        for allocation in self:
            i = 0
            (current_level, current_level_idx) = allocation._get_current_accrual_plan_level_id(allocation.nextcall)
            print('allocation : ', allocation, allocation.nextcall)
            forcasted_days = 0
            if current_level:
                nextcall = current_level._get_next_date(allocation.nextcall)
                print('next call', nextcall, leave_start_date)
                while nextcall <= leave_start_date:
                    print('i : ', i)
                    nextcall = current_level._get_next_date(nextcall)
                    print('hiiii', nextcall)
                    i += 1
                forcasted_days = i * current_level.added_value
                print('gegege...',forcasted_days)
                print('geg22ege...',current_level.added_value)
        return forcasted_days

        # if self._get_next_date_edited(self.last)

    def _get_current_accrual_plan_level_id(self, date, level_ids=False):
        """
        Returns a pair (accrual_plan_level, idx) where accrual_plan_level is the level for the given date
         and idx is the index for the plan in the ordered set of levels
        """
        self.ensure_one()
        if not self.accrual_plan_id.level_ids:
            return (False, False)
        # Sort by sequence which should be equivalent to the level
        if not level_ids:
            level_ids = self.accrual_plan_id.level_ids.sorted('sequence')
        current_level = False
        current_level_idx = -1
        for idx, level in enumerate(level_ids):
            if date:
                if date > self.date_from + get_timedelta(level.start_count, level.start_type):
                    current_level = level
                    current_level_idx = idx
        # If transition_mode is set to `immediately` or we are currently on the first level
        # the current_level is simply the first level in the list.
        if current_level_idx <= 0 or self.accrual_plan_id.transition_mode == "immediately":
            return (current_level, current_level_idx)
        # In this case we have to verify that the 'previous level' is not the current one due to `end_of_accrual`
        level_start_date = self.date_from + get_timedelta(current_level.start_count, current_level.start_type)
        previous_level = level_ids[current_level_idx - 1]
        # If the next date from the current level's start date is before the last call of the previous level
        # return the previous level
        if current_level._get_next_date(level_start_date) < previous_level._get_next_date(level_start_date):
            return (previous_level, current_level_idx - 1)
        return (current_level, current_level_idx)


class AcoHrLeaveInh(models.Model):
    _inherit = 'hr.leave.type'
    Forecast_Future_Allocation = fields.Boolean('Forecast_Future_Allocation', default=False)


class AcoHrLeaveInh(models.Model):
    _inherit = 'hr.leave.accrual.level'

    def _get_next_date_edited(self, last_call):
        """
        Returns the next date with the given last call
        """

        self.ensure_one()
        if self.frequency == 'daily':
            return last_call + relativedelta(days=1)
        elif self.frequency == 'weekly':
            daynames = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
            weekday = daynames.index(self.week_day)
            return last_call + relativedelta(days=1, weekday=weekday)
        elif self.frequency == 'bimonthly':
            first_date = last_call + relativedelta(day=self.first_day)
            second_date = last_call + relativedelta(day=self.second_day)
            if last_call < first_date:
                return first_date
            elif last_call < second_date:
                return second_date
            else:
                return last_call + relativedelta(months=1, day=self.first_day)
        elif self.frequency == 'monthly':
            date = last_call + relativedelta(day=self.first_day)
            if last_call < date:
                return date
            else:
                return last_call + relativedelta(months=1, day=self.first_day)
        elif self.frequency == 'biyearly':
            first_month = MONTHS.index(self.first_month) + 1
            second_month = MONTHS.index(self.second_month) + 1
            first_date = last_call + relativedelta(month=first_month, day=self.first_month_day)
            second_date = last_call + relativedelta(month=second_month, day=self.second_month_day)
            if last_call < first_date:
                return first_date
            elif last_call < second_date:
                return second_date
            else:
                return last_call + relativedelta(years=1, month=first_month, day=self.first_month_day)
        elif self.frequency == 'yearly':
            month = MONTHS.index(self.yearly_month) + 1
            date = last_call + relativedelta(month=month, day=self.yearly_day)
            if last_call < date:
                return date
            else:
                return last_call + relativedelta(years=1, month=month, day=self.yearly_day)
        else:
            return False
