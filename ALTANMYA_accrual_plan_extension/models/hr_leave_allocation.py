from collections import defaultdict

from odoo.addons.resource.models.resource import HOURS_PER_DAY
from odoo import api, fields, models, _

from datetime import datetime
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

    @api.depends('holiday_status_id', 'allocation_type', 'number_of_hours_display', 'number_of_days_display', 'date_to')
    def _compute_from_holiday_status_id_with_emp(self, employee_id):
        print('gets executed ')
        today = fields.Date.today()
        first_day_this_year = today + relativedelta(month=1, day=1)
        accrual_allocations = self.filtered(
            lambda alloc: alloc.allocation_type == 'accrual' and not alloc.accrual_plan_id and alloc.holiday_status_id)
        accruals_dict = {}
        if accrual_allocations:
            accruals_read_group = self.env['hr.leave.accrual.plan'].read_group(
                [('time_off_type_id', 'in', accrual_allocations.holiday_status_id.ids)],
                ['time_off_type_id', 'ids:array_agg(id)'],
                ['time_off_type_id'],
            )
            accruals_dict = {res['time_off_type_id'][0]: res['ids'] for res in accruals_read_group}
        for allocation in self:
            allocation.number_of_days = allocation.number_of_days_display
            if allocation.type_request_unit == 'hour':
                allocation.number_of_days = allocation.number_of_hours_display / (
                        employee_id.sudo().resource_calendar_id.hours_per_day or HOURS_PER_DAY)
            if allocation.accrual_plan_id.time_off_type_id.id not in (False, allocation.holiday_status_id.id):
                allocation.accrual_plan_id = False
            if allocation.allocation_type == 'accrual' and not allocation.accrual_plan_id:
                if allocation.holiday_status_id:
                    allocation.accrual_plan_id = accruals_dict.get(allocation.holiday_status_id.id, [False])[0]

            print('acc plan ', allocation.accrual_plan_id)
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
                        number_of_days_since_the_start_of_year = today - first_day_this_year
                        print('dddddddd : ', number_of_days_since_the_start_of_year.days)
                        if grace_period_in_days < number_of_days_since_the_start_of_year.days:
                            employee_days_per_allocation = self.holiday_status_id._get_employees_days_per_allocation_in_this_year(
                                employee_id.ids)
                            print('employee_days_per_allocation: ', employee_days_per_allocation)
                            for allocation in self:
                                allocation.max_leaves = allocation.number_of_hours_display if allocation.type_request_unit == 'hour' else allocation.number_of_days
                                allocation.leaves_taken = \
                                    employee_days_per_allocation[employee_id.id][
                                        allocation.holiday_status_id][
                                        allocation]['remaining_leaves']
                                taken_leaves = employee_days_per_allocation[employee_id.id][
                                    allocation.holiday_status_id][
                                    allocation]['virtual_leaves_taken']
                                print('days per allocations : ',
                                      employee_days_per_allocation[employee_id.id][
                                          allocation.holiday_status_id][
                                          allocation]['virtual_leaves_taken'])
                                print('max leaves ', allocation.max_leaves)
                                print('diff is : ', allocation.max_leaves - employee_days_per_allocation[employee_id.id][
                                          allocation.holiday_status_id][
                                          allocation]['virtual_leaves_taken'])
                                # last_year_postponed_days = 20
                                if taken_leaves < allocation.last_year_postponed_days:
                                    allocation.number_of_days -= (allocation.last_year_postponed_days - taken_leaves)
                                    allocation.is_grace_period_passed = True
                                else:
                                    allocation.is_grace_period_passed = True
                                # allocation.number_of_days = allocation.number_of_days -

                                # If I suppose that the taken leaves are in this year then if
                                # the difference between the past year left days and
    #
    # def _get_current_accrual_plan_level_id(self, date, level_ids=False):
    #     """
    #     Returns a pair (accrual_plan_level, idx) where accrual_plan_level is the level for the given date
    #      and idx is the index for the plan in the ordered set of levels
    #     """
    #     self.ensure_one()
    #     if not self.accrual_plan_id.level_ids:
    #         return (False, False)
    #     # Sort by sequence which should be equivalent to the level
    #     if not level_ids:
    #         level_ids = self.accrual_plan_id.level_ids.sorted('sequence')
    #     print('all levels : ', level_ids)
    #     current_level = False
    #     current_level_idx = -1
    #     for idx, level in enumerate(level_ids):
    #         start_count = level.start_count if level.based_on_contract_or_allocation == 'allocation' else level.contract_start_count
    #         start_type = level.start_type if level.based_on_contract_or_allocation == 'allocation' else level.contract_start_type
    #         print(level, 'date ', date, self.date_from + get_timedelta(start_count, start_type),
    #               get_timedelta(start_count, start_type))
    #         if date > self.date_from + get_timedelta(start_count, start_type):
    #             print('level is : ', level)
    #             current_level = level
    #             current_level_idx = idx
    #     # If transition_mode is set to `immediately` or we are currently on the first level
    #     # the current_level is simply the first level in the list.
    #     if current_level_idx <= 0 or self.accrual_plan_id.transition_mode == "immediately":
    #         return (current_level, current_level_idx)
    #     # In this case we have to verify that the 'previous level' is not the current one due to `end_of_accrual`
    #     start_count2 = current_level.start_count if current_level.based_on_contract_or_allocation == 'allocation' else current_level.contract_start_count
    #     start_type2 = current_level.start_type if current_level.based_on_contract_or_allocation == 'allocation' else current_level.contract_start_type
    #     level_start_date = self.date_from + get_timedelta(start_count2, start_type2)
    #     previous_level = level_ids[current_level_idx - 1]
    #     # If the next date from the current level's start date is before the last call of the previous level
    #     # return the previous level
    #     if current_level._get_next_date(level_start_date) < previous_level._get_next_date(level_start_date):
    #         return (previous_level, current_level_idx - 1)
    #     return (current_level, current_level_idx)
    #
    # def _process_accrual_plans(self, date_to=False, force_period=False):
    #     """
    #     This method is part of the cron's process.
    #     The goal of this method is to retroactively apply accrual plan levels and progress from nextcall to date_to or today.
    #     If force_period is set, the accrual will run until date_to in a prorated way (used for end of year accrual actions).
    #     """
    #     date_to = date_to or fields.Date.today()
    #     first_allocation = _(
    #         """This allocation have already ran once, any modification won't be effective to the days allocated to the employee. If you need to change the configuration of the allocation, cancel and create a new one.""")
    #     for allocation in self:
    #         level_ids = allocation.accrual_plan_id.level_ids.sorted('sequence')
    #         if not level_ids:
    #             continue
    #         if not allocation.nextcall:
    #             first_level = level_ids[0]
    #             start_count = first_level.start_count if first_level.based_on_contract_or_allocation == 'allocation' else first_level.contract_start_count
    #             start_type = first_level.start_type if first_level.based_on_contract_or_allocation == 'allocation' else first_level.contract_start_type
    #             first_level_start_date = allocation.date_from + get_timedelta(start_count, start_type)
    #             if date_to < first_level_start_date:
    #                 # Accrual plan is not configured properly or has not started
    #                 continue
    #             allocation.lastcall = max(allocation.lastcall, first_level_start_date)
    #             allocation.nextcall = first_level._get_next_date(allocation.lastcall)
    #             if len(level_ids) > 1:
    #                 start_count = level_ids[1].start_count if level_ids[
    #                                                               1].based_on_contract_or_allocation == 'allocation' else \
    #                     level_ids[1].contract_start_count
    #                 start_type = level_ids[1].start_type if level_ids[
    #                                                             1].based_on_contract_or_allocation == 'allocation' else \
    #                     level_ids[1].contract_start_type
    #                 second_level_start_date = allocation.date_from + get_timedelta(start_count,
    #                                                                                start_type)
    #                 allocation.nextcall = min(second_level_start_date, allocation.nextcall)
    #             allocation._message_log(body=first_allocation)
    #         days_added_per_level = defaultdict(lambda: 0)
    #         while allocation.nextcall <= date_to:
    #             (current_level, current_level_idx) = allocation._get_current_accrual_plan_level_id(allocation.nextcall)
    #             nextcall = current_level._get_next_date(allocation.nextcall)
    #             # Since _get_previous_date returns the given date if it corresponds to a call date
    #             # this will always return lastcall except possibly on the first call
    #             # this is used to prorate the first number of days given to the employee
    #             period_start = current_level._get_previous_date(allocation.lastcall)
    #             period_end = current_level._get_next_date(allocation.lastcall)
    #             # Also prorate this accrual in the event that we are passing from one level to another
    #             if current_level_idx < (
    #                     len(level_ids) - 1) and allocation.accrual_plan_id.transition_mode == 'immediately':
    #                 next_level = level_ids[current_level_idx + 1]
    #                 start_count = next_level.start_count if next_level.based_on_contract_or_allocation == 'allocation' else next_level.contract_start_count
    #                 start_type = next_level.start_type if next_level.based_on_contract_or_allocation == 'allocation' else next_level.contract_start_type
    #
    #                 current_level_last_date = allocation.date_from + get_timedelta(start_count,
    #                                                                                start_type)
    #                 if allocation.nextcall != current_level_last_date:
    #                     nextcall = min(nextcall, current_level_last_date)
    #             # We have to check for end of year actions if it is within our period
    #             #  since we can create retroactive allocations.
    #             if allocation.lastcall.year < allocation.nextcall.year and \
    #                     current_level.action_with_unused_accruals == 'postponed' and \
    #                     current_level.postpone_max_days > 0:
    #                 # Compute number of days kept
    #                 allocation_days = allocation.number_of_days - allocation.leaves_taken
    #                 allowed_to_keep = max(0, current_level.postpone_max_days - allocation_days)
    #                 number_of_days = min(allocation_days, current_level.postpone_max_days)
    #                 allocation.number_of_days = number_of_days + allocation.leaves_taken
    #                 total_gained_days = sum(days_added_per_level.values())
    #                 days_added_per_level.clear()
    #                 days_added_per_level[current_level] = min(total_gained_days, allowed_to_keep)
    #             gained_days = allocation._process_accrual_plan_level(
    #                 current_level, period_start, allocation.lastcall, period_end, allocation.nextcall)
    #             days_added_per_level[current_level] += gained_days
    #             if current_level.maximum_leave > 0 and sum(days_added_per_level.values()) > current_level.maximum_leave:
    #                 days_added_per_level[current_level] -= sum(
    #                     days_added_per_level.values()) - current_level.maximum_leave
    #
    #             allocation.lastcall = allocation.nextcall
    #             allocation.nextcall = nextcall
    #             if force_period and allocation.nextcall > date_to:
    #                 allocation.nextcall = date_to
    #                 force_period = False
    #
    #         if days_added_per_level:
    #             number_of_days_to_add = allocation.number_of_days + sum(days_added_per_level.values())
    #             # Let's assume the limit of the last level is the correct one
    #             allocation.number_of_days = min(number_of_days_to_add,
    #                                             current_level.maximum_leave + allocation.leaves_taken) if current_level.maximum_leave > 0 else number_of_days_to_add
