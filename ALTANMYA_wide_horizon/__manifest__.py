# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Wide Horizon',
    'version': '1.0',
    'sequence': -201,
    'depends': ['base', 'hr', 'hr_contract', 'hr_payroll'],
    'data': [
        'data/cron.xml',
        'data/activity_noti.xml',
        'data/mail_for_notify.xml',
        'views/hr_contract.xml',
        'views/hr_employee.xml',
        'views/res_config_settings_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
