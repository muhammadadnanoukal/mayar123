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


class HrWorkEntryInh(models.Model):
    _name = 'hr.work.entry.inh'

    test = fields.Char(string='Excel File')

    # def import_excel_data(self):
    #     # Add your code here to process the uploaded Excel file
    #     print('file uploaded')
    #     pass

class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    test = fields.Char(string='Excel File')
    attachment = fields.Binary(string='Attachment')
