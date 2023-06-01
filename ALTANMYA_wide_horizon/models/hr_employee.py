from odoo import models, api, fields
from dateutil.relativedelta import relativedelta
from datetime import datetime


class HrEmployeeCSV(models.Model):
    _inherit = ['hr.employee']

    iqama_issue_date = fields.Date(string="Iqama Issue Date")
    iqama_expiry_date = fields.Date(string="Iqama Expiry Date")
    iqama_attachment = fields.Binary(string="Iqama Attachment")

    passport_expiry = fields.Date(string="Passport Expiry")
    passport_attachment = fields.Binary(string="Passport Attachment")

    border_number = fields.Char(string="Border No")
    sponsorship_number = fields.Char(string="Sponsorship No")

    visa_attachment = fields.Binary(string="VISA Attachment")

    @api.model
    def hr_employee_notification_scheduled_action(self):
        # now = datetime.now()
        now_date = datetime.now().date()
        period = self.env['ir.config_parameter'].get_param('ALTANMYA_wide_horizon.notified_period')
        period_template = self.env['ir.config_parameter'].get_param('ALTANMYA_wide_horizon.notified_email_template')
        period_user_name = self.env['ir.config_parameter'].get_param('ALTANMYA_wide_horizon.notified_email_user')
        records = self.env['hr.employee'].search([('id', '>', -1)])
        template = self.env['mail.template'].search([('id', '=', int(period_template))])
        period_user = self.env['res.users'].search([('id', '=', int(period_user_name))])
        for rec in records:
            check = False
            if rec.iqama_expiry_date:
                if rec.iqama_expiry_date <= (now_date + relativedelta(days=int(period))):
                    rec.activity_schedule('ALTANMYA_wide_horizon.mail_activity_expiration_date_wide_horizon',
                                          user_id=period_user.id, note=f'iqama is about to expire')
                    # template.send_mail(rec.id)
                    check = True

            if rec.passport_expiry:
                if rec.passport_expiry <= (now_date + relativedelta(days=int(period))):
                    rec.activity_schedule('ALTANMYA_wide_horizon.mail_activity_expiration_date_wide_horizon',
                                          user_id=period_user.id, note=f'passport is about to expire')
                    # template.send_mail(rec.id)
                    check = True

            if rec.visa_expire:
                if rec.visa_expire <= (now_date + relativedelta(days=int(period))):
                    rec.activity_schedule('ALTANMYA_wide_horizon.mail_activity_expiration_date_wide_horizon',
                                          user_id=period_user.id, note=f'visa is about to expire')
                    # template.send_mail(rec.id)
                    check = True

            if rec.work_permit_expiration_date:
                if rec.work_permit_expiration_date <= (now_date + relativedelta(days=int(period))):
                    rec.activity_schedule('ALTANMYA_wide_horizon.mail_activity_expiration_date_wide_horizon',
                                          user_id=period_user.id, note=f'work permit is about to expire')
                    # template.send_mail(rec.id)
                    check = True

            if check:
                template.send_mail(rec.id)
            check = False

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        domain = []
        if args is None:
            args = []
        if name:
            domain = ['|', ('name', 'ilike', name), ('registration_number', '=', name)]
            if args:
                domain += args
        return self._search(domain, limit=limit, access_rights_uid=name_get_uid)

    def name_get(self):
        result = []
        for rec in self:
            name = '[' + str(rec.registration_number) + '] ' + rec.name
            result.append((rec.id, name))
        return result
