from collections import defaultdict

from odoo.addons.resource.models.resource import HOURS_PER_DAY
from odoo import api, fields, models, _

from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from odoo.tools import get_timedelta


class HolidaysAllocation(models.Model):
    """ Allocation Requests Access specifications: similar to leave requests """
    _inherit = "hr.leave.allocation"
    _description = "Time Off Allocation"

    is_grace_period_passed = fields.Boolean('Is grace period passed', default=True)
    last_year_postponed_days = fields.Integer('Last year postponed days')

    @api.model_create_multi
    def create(self, vals_list):
        holidays = super().create(vals_list)
        holidays.write({'is_grace_period_passed' : True})
        return holidays

    def _end_of_year_accrual(self):
        # to override in payroll
        today = fields.Date.today()
        last_day_last_year = today + relativedelta(years=-1, month=12, day=31)
        first_day_this_year = today + relativedelta(month=1, day=1)

        # first_day_this_year = datetime.strptime('2024-01-01', '%Y-%m-%d').date()
        # last_day_last_year = datetime.strptime('2024-12-31', '%Y-%m-%d').date()

        for allocation in self:
            current_level = allocation._get_current_accrual_plan_level_id(first_day_this_year)[0]
            if not current_level:
                continue
            print('curr lvl ', current_level)
            lastcall = current_level._get_previous_date(first_day_this_year)
            nextcall = current_level._get_next_date(first_day_this_year)
            if current_level.action_with_unused_accruals == 'lost':
                print('lastcall lost ', lastcall)
                if lastcall == first_day_this_year:
                    lastcall = current_level._get_previous_date(first_day_this_year - relativedelta(days=1))
                    nextcall = first_day_this_year
                    print('last and next: ', lastcall, nextcall)
                print('num of days ',  allocation.leaves_taken)
                # Allocations are lost but number_of_days should not be lower than leaves_taken
                allocation.write({'number_of_days': allocation.leaves_taken, 'lastcall': lastcall, 'nextcall': nextcall})
            elif current_level.action_with_unused_accruals == 'postponed' and current_level.postpone_max_days:
                # Make sure the period was ran until the last day of last year
                if allocation.nextcall:
                    allocation.nextcall = last_day_last_year
                allocation._process_accrual_plans(last_day_last_year, True)
                number_of_days = min(allocation.number_of_days - allocation.leaves_taken, current_level.postpone_max_days) + allocation.leaves_taken
                print('data : ', min(allocation.number_of_days - allocation.leaves_taken, current_level.postpone_max_days), ' ,, ', allocation.leaves_taken)
                print('number of days : ', number_of_days)
                allocation.write({'number_of_days': number_of_days, 'lastcall': lastcall, 'nextcall': nextcall})
                allocation.write({'is_grace_period_passed': False, 'last_year_postponed_days': number_of_days})
                print('allocation : ', allocation)

    # @api.depends('holiday_status_id', 'allocation_type', 'number_of_hours_display', 'number_of_days_display', 'date_to')
    # def _compute_from_holiday_status_id_with_emp(self, employee_id):
    #     print('gets executed ')
    #     today = fields.Date.today()
    #     first_day_this_year = today + relativedelta(month=1, day=1)
    #     accrual_allocations = self.filtered(
    #         lambda alloc: alloc.allocation_type == 'accrual' and not alloc.accrual_plan_id and alloc.holiday_status_id)
    #     accruals_dict = {}
    #     if accrual_allocations:
    #         accruals_read_group = self.env['hr.leave.accrual.plan'].read_group(
    #             [('time_off_type_id', 'in', accrual_allocations.holiday_status_id.ids)],
    #             ['time_off_type_id', 'ids:array_agg(id)'],
    #             ['time_off_type_id'],
    #         )
    #         accruals_dict = {res['time_off_type_id'][0]: res['ids'] for res in accruals_read_group}
    #     for allocation in self:
    #         allocation.number_of_days = allocation.number_of_days_display
    #         if allocation.type_request_unit == 'hour':
    #             allocation.number_of_days = allocation.number_of_hours_display / (
    #                     employee_id.sudo().resource_calendar_id.hours_per_day or HOURS_PER_DAY)
    #         if allocation.accrual_plan_id.time_off_type_id.id not in (False, allocation.holiday_status_id.id):
    #             allocation.accrual_plan_id = False
    #         if allocation.allocation_type == 'accrual' and not allocation.accrual_plan_id:
    #             if allocation.holiday_status_id:
    #                 allocation.accrual_plan_id = accruals_dict.get(allocation.holiday_status_id.id, [False])[0]
    #
    #         print('acc plan ', allocation.accrual_plan_id)
    #         if allocation.accrual_plan_id:
    #             current_level = self.env['hr.leave.accrual.level']
    #             if allocation.nextcall:
    #                 current_level = allocation._get_current_accrual_plan_level_id(allocation.nextcall)[0]
    #                 print('current level is : ', current_level)
    #             if current_level and not allocation.is_grace_period_passed:
    #                 if current_level.action_with_unused_accruals == 'postponed' and current_level.grace_period:
    #                     print('grace period : ', current_level.grace_period)
    #                     grace_type_multipliers = {
    #                         'day': 1,
    #                         'month': 30,
    #                     }
    #                     first_day_this_year = today + relativedelta(month=1, day=1)
    #                     grace_period_in_days = current_level.grace_period * grace_type_multipliers[
    #                         current_level.grace_type]
    #                     print('grace period in days', grace_period_in_days)
    #                     # needs to check for the next year start date
    #                     number_of_days_since_the_start_of_year = today - first_day_this_year
    #                     print('dddddddd : ', number_of_days_since_the_start_of_year.days)
    #                     if grace_period_in_days < number_of_days_since_the_start_of_year.days:
    #                         employee_days_per_allocation = self.holiday_status_id._get_employees_days_per_allocation_in_this_year(
    #                             employee_id.ids)
    #                         print('employee_days_per_allocation: ', employee_days_per_allocation)
    #                         for allocation in self:
    #                             allocation.max_leaves = allocation.number_of_hours_display if allocation.type_request_unit == 'hour' else allocation.number_of_days
    #                             allocation.leaves_taken = \
    #                                 employee_days_per_allocation[employee_id.id][
    #                                     allocation.holiday_status_id][
    #                                     allocation]['remaining_leaves']
    #                             taken_leaves = employee_days_per_allocation[employee_id.id][
    #                                 allocation.holiday_status_id][
    #                                 allocation]['virtual_leaves_taken']
    #                             print('days per allocations : ',
    #                                   employee_days_per_allocation[employee_id.id][
    #                                       allocation.holiday_status_id][
    #                                       allocation]['virtual_leaves_taken'])
    #                             print('max leaves ', allocation.max_leaves)
    #                             print('diff is : ', allocation.max_leaves - employee_days_per_allocation[employee_id.id][
    #                                       allocation.holiday_status_id][
    #                                       allocation]['virtual_leaves_taken'])
    #                             # last_year_postponed_days = 20
    #                             if taken_leaves < allocation.last_year_postponed_days:
    #                                 allocation.number_of_days -= (allocation.last_year_postponed_days - taken_leaves)
    #                                 allocation.is_grace_period_passed = True
    #                             else:
    #                                 allocation.is_grace_period_passed = True
                                # allocation.number_of_days = allocation.number_of_days -

                                # If I suppose that the taken leaves are in this year then if
                                # the difference between the past year left days and

    def check_grace_period(self):
        # Get the current date to determine the start and end of the accrual period
        today = datetime.combine(fields.Date.today(), time(0, 0, 0))
        # this_year_first_day = (today + relativedelta(day=1, month=1)).date()
        # this_year_first_day = '2024-01-01'
        allocations = self.search(
            [('allocation_type', '=', 'accrual'), ('state', '=', 'validate'), ('accrual_plan_id', '!=', False),
             ('employee_id', '!=', False),
             '|', ('date_to', '=', False), ('date_to', '>', fields.Datetime.now()),
             ('is_grace_period_passed', '=', False)])
        print('allocations in check grace period ', allocations)
        for allocation in allocations:
            if allocation.accrual_plan_id:
                current_level = self.env['hr.leave.accrual.level']
                if allocation.nextcall:
                    current_level = allocation._get_current_accrual_plan_level_id(allocation.nextcall)[0]
                    print('current level is : ', current_level)
                if current_level and not allocation.is_grace_period_passed:
                    if current_level.action_with_unused_accruals == 'postponed' and current_level.grace_period:
                        print('grace period : ', current_level.grace_period)
                        grace_type_multipliers = {
                            'day': 1,
                            'month': 30,
                        }
                        grace_period_in_days = current_level.grace_period * grace_type_multipliers[
                            current_level.grace_type]
                        print('grace period in days', grace_period_in_days)
                        # needs to check for the next year start date
                        first_day_this_year = today + relativedelta(month=1, day=1)
                        number_of_days_since_the_start_of_year = today - first_day_this_year
                        print('dddddddd : ', number_of_days_since_the_start_of_year.days)
                        if grace_period_in_days < number_of_days_since_the_start_of_year.days:
                            employee_days_per_allocation = allocation.holiday_status_id._get_employees_days_per_allocation_in_this_year(
                                allocation.employee_id.ids)
                            print('employee_days_per_allocation: ', employee_days_per_allocation)

                            allocation.max_leaves = allocation.number_of_hours_display if allocation.type_request_unit == 'hour' else allocation.number_of_days
                            allocation.leaves_taken = \
                                employee_days_per_allocation[allocation.employee_id.id][
                                    allocation.holiday_status_id][
                                    allocation]['remaining_leaves']
                            taken_leaves = employee_days_per_allocation[allocation.employee_id.id][
                                allocation.holiday_status_id][
                                allocation]['virtual_leaves_taken']
                            print('days per allocations : ',
                                  employee_days_per_allocation[allocation.employee_id.id][
                                      allocation.holiday_status_id][
                                      allocation]['virtual_leaves_taken'])
                            print('max leaves ', allocation.max_leaves)
                            print('diff is : ', allocation.max_leaves - employee_days_per_allocation[allocation.employee_id.id][
                                      allocation.holiday_status_id][
                                      allocation]['virtual_leaves_taken'])
                            # last_year_postponed_days = 20
                            if taken_leaves < allocation.last_year_postponed_days:
                                allocation.number_of_days -= (allocation.last_year_postponed_days - taken_leaves)
                                allocation.is_grace_period_passed = True
                            else:
                                allocation.is_grace_period_passed = True