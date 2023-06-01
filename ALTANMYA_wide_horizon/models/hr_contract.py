from odoo import models, api, fields
from dateutil.relativedelta import relativedelta
from datetime import datetime


class HrContract(models.Model):
    _inherit = 'hr.contract'

    contract_period_month = fields.Integer(string="Conract Period (Month)")
    copied_record = fields.Boolean(string="copied record")

    @api.model
    def hr_contract_duplication_scheduled_action(self):
        now = datetime.now()
        records = self.env['hr.contract'].search([('state', '=', 'open')])
        for rec in records:
            if rec.date_end:
                if not rec.copied_record:
                    if rec.date_end.strftime('%Y-%m-%d') == now.strftime('%Y-%m-%d'):
                        rec.copy()

    @api.onchange('contract_period_month')
    def compute_date_end(self):
        for rec in self:
            if rec.contract_period_month:
                rec.date_end = rec.date_start + relativedelta(months=rec.contract_period_month) - relativedelta(days=1)

    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('date_start'):
            if self.contract_period_month == 0:
                default['date_end'] = None
                default['date_start'] = self.date_end + relativedelta(days=1)
                default['copied_record'] = False
                self.copied_record = True
            else:
                default['date_end'] = self.date_end + relativedelta(months=self.contract_period_month)
                default['date_start'] = self.date_end + relativedelta(days=1)
                if default['date_start'] <= default['date_end']:
                    default['copied_record'] = False
                    self.copied_record = True
        return super(HrContract, self).copy(default)
