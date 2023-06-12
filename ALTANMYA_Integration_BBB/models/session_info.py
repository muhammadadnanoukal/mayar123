from odoo import api, fields, models
import logging
import base64
import hashlib
from urllib.parse import urlencode
import urllib.parse
from odoo import api, fields, models, _
import uuid
import requests
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SessionInfo(models.Model):
    _name = 'session.info'

    meeting_id = fields.Integer('meeting id')
