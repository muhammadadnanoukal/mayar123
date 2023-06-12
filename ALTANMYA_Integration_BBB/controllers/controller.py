import ast

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError
from datetime import datetime, timedelta
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo import http
import hashlib
import xml.etree.ElementTree as ET

from odoo.addons.web.controllers.report import ReportController
from odoo.tools import format_datetime, format_date, is_html_empty
from dateutil.relativedelta import relativedelta

from odoo.http import request, Response
from odoo.http import request
from werkzeug.utils import redirect

from urllib.parse import urlencode
import urllib.parse
from odoo import api, fields, models, _
import uuid
import requests
import base64


class getmeeting(http.Controller):
    @http.route('/meeting', auth='user', type='http', website=True)
    def gotomeetings(self, survey_id=None, **kw):
        meetings = request.env['integration.bbb'].search([])
        # print('asd12321asd==>', meetings.meeting_id)
        if not meetings:
            print('mmmmdata==>', meetings)
            return http.request.render("ALTANMYA_Integration_BBB.no_data", {})
        else:
            return http.request.render("ALTANMYA_Integration_BBB.show_meet", {'meetings': meetings})

    @http.route('/meeting/<int:meeting_id>', auth='user', type='http', website=True)
    def joinmeeting(self, meeting_id, **kw):
        meeting = request.env['integration.bbb'].sudo().browse(meeting_id)
        print('kokokomeeting_id==>', (meeting))
        base_url = "https://bbb.al-tanmyah.com/bigbluebutton/api/join"

        params = {
            'fullName': request.env.user.name if request.env.user else 'user',
            'meetingID': meeting.meeting_id,
            'role': "MODERATOR" if meeting.is_MODERATOR else 'VIEWER',  # Use the stored role
        }

        shared_secret = 'n2IltrMMWTwsQ4f5WP8QGIGrRplSMfjhKUmhWBvdUk'
        call = 'join'

        query_string = urllib.parse.urlencode(params)
        print('suiiiiiiiii=>', query_string)
        concatenated_string = call + query_string + shared_secret
        checksum = hashlib.sha1(concatenated_string.encode('utf-8')).hexdigest()
        print('suiichecksum==>', checksum)
        params['checksum'] = checksum

        request_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        response = requests.get(request_url)
        print('joinjoin', response)
        print('request_url suiiiiiii==>', request_url)
        if response.status_code == 200:
            try:
                xml_response = ET.fromstring(response.content)
                return_code = xml_response.find('returncode').text
                if return_code == 'FAILED':
                    message = xml_response.find('message').text
                    return http.request.render("ALTANMYA_Integration_BBB.no_meet", {})
                else:
                    return """
                           <script type="text/javascript">
                               window.open('{request_url}', '_blank');
                           </script>
                           """.format(request_url=request_url)
            except ET.ParseError:
                return """
                      <script type="text/javascript">
                               window.open('{request_url}', '_blank');
                           </script>
                           """.format(request_url=request_url)
        else:
            return http.request.render("ALTANMYA_Integration_BBB.no_meet", {})
