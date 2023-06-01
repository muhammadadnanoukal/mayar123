from odoo import models, api, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    notified_period = fields.Integer(string="Notified Period Days", help="Notified Period Days",
                                     config_parameter='ALTANMYA_wide_horizon.notified_period', required=True)

    notified_email_template = fields.Many2one('mail.template', string="Notified Period Email Template",
                                              help="Notified Period Email Template",
                                              config_parameter='ALTANMYA_wide_horizon.notified_email_template', required=True)

    notified_email_user = fields.Many2one('res.users', string="Notified Period User",
                                          help="Notified Period User",
                                          config_parameter='ALTANMYA_wide_horizon.notified_email_user', required=True)
