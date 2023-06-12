from odoo import api, fields, models
import logging
from lxml import etree
import base64
import hashlib
from urllib.parse import urlencode
import urllib.parse
from odoo import api, fields, models, _
import uuid
import requests
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IntegrationBBB(models.Model):
    _name = 'integration.bbb'

    name = fields.Char(string='Name', required=True)
    record = fields.Boolean(default=False, string='Record', required=True)
    meeting_id = fields.Char(string='Meeting ID', readonly=True)
    record_id = fields.Char(string='Record ID', readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    # Add a selection field to store the role
    role = fields.Selection([
        ('MODERATOR', 'Moderator'),
        ('VIEWER', 'Viewer'),
    ], string='Role', default='MODERATOR')

    pdf_file = fields.Binary(string='PDF File')  # Add a binary field for the PDF file
    duration_minutes = fields.Integer(string='Duration (Minutes)')
    is_MODERATOR = fields.Boolean(default=False, string='is_MODERATOR')
    prevent_camera = fields.Boolean(default=False, string='prevent users from sharing their camera')
    user_listen_only = fields.Boolean(default=False, string='allow user to join listen only')
    disable_private_chats = fields.Boolean(default=False, string='disable private chats in the meeting')
    disable_public_chats = fields.Boolean(default=False, string='disable public chat in the meeting')
    disable_notes_chats = fields.Boolean(default=False, string='disable notes in the meeting')
    prevent_viewers_seeing = fields.Boolean(default=False, string='prevent viewers from seeing other viewers in the user list')
    meeting_end_if_after = fields.Boolean(default=False, string='meeting will end automatically after a delay if no moderator')
    min_to_end = fields.Integer(string='ended after this many minutes')

    @api.model
    def create(self, vals):
        new_record = super(IntegrationBBB, self).create(vals)
        new_record.create_bigbluebutton_room()
        return new_record

    # function create meeting
    def create_bigbluebutton_room(self):
        base_url = "http://test-install.blindsidenetworks.com/bigbluebutton/api/create"

        meeting_id = str(uuid.uuid4())  # Generate a unique meeting ID

        params = {
            'name': self.name or 'MyRoom',
            'meetingID': meeting_id,
            'record': str(self.record or False),
            'welcome': 'Welcome guys  ',
            'logoutURL': 'http://localhost:8069//@/meeting',
            'duration': self.duration_minutes,
            'lockSettingsDisableCam': self.prevent_camera,
            'lockSettingsDisableMic': self.user_listen_only,
            'lockSettingsDisablePrivateChat': self.disable_private_chats,
            'lockSettingsDisablePublicChat': self.disable_public_chats,
            'lockSettingsHideUserList': self.prevent_viewers_seeing,
            'endWhenNoModerator': self.meeting_end_if_after,
            'endWhenNoModeratorDelayInMinutes': self.min_to_end,
        }
        print('params create==>',params)
        shared_secret = '8cd8ef52e8e101574e400365b55e11a6'  # Replace with your actual shared secret
        call = 'create'

        query_string = urllib.parse.urlencode(params)
        print('query_string', query_string)
        concatenated_string = call + query_string + shared_secret
        print('concatenated_string', concatenated_string)
        checksum = hashlib.sha1(concatenated_string.encode('utf-8')).hexdigest()
        print('checksum', checksum)
        params['checksum'] = checksum

        request_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        response = requests.post(request_url)
        print('request_url==>', request_url)

        # Handle the response and perform necessary actions
        print('asd', response.content)  #
        # Handle the response and perform necessary actions
        join_url = response.content.decode('utf-8')
        # self.write({'meeting_id': meeting_id, 'join_url': join_url})
        print('b6e5meeting_id==>', meeting_id)
        self.meeting_id = meeting_id  # Store the meeting ID in the record
        return meeting_id

    # function join meeting
    def join_bigbluebutton_room(self):
        base_url = "http://test-install.blindsidenetworks.com/bigbluebutton/api/join"
        # meeting_id = str(uuid.uuid4())
        # meeting_id = self.create_bigbluebutton_room()
        meeting_id = self.meeting_id  # Retrieve the stored meeting ID
        print('5rameeting_id==>', meeting_id)
        params = {
                'fullName': self.user_id.name if self.user_id else '',
            'meetingID': meeting_id,
            'role': self.role,  # Use the stored role
        }

        shared_secret = '8cd8ef52e8e101574e400365b55e11a6'

        call = 'join'

        query_string = urllib.parse.urlencode(params)
        concatenated_string = call + query_string + shared_secret
        checksum = hashlib.sha1(concatenated_string.encode('utf-8')).hexdigest()
        print('join checksum==>', checksum)
        params['checksum'] = checksum

        request_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        print('join request_url==>', request_url)
        response = requests.get(request_url)
        print('joinjoin', response)

        # try:
        #     response = requests.get(request_url)
        #     response.raise_for_status()
        # except requests.exceptions.RequestException as e:
        #     _logger.error(f'Error when joining BBB room: {str(e)}')
        #     raise UserError(_('An error occurred when joining the BBB room. Please try again later.'))

        try:
            response_xml = etree.fromstring(response.content)
            return_code = response_xml.findtext('returncode')
            if return_code == 'FAILED':
                message_key = response_xml.findtext('messageKey')
                if message_key == 'notFound':
                    raise UserError(_('The meeting has ended.'))
                else:
                    raise UserError(_('An error occurred when joining the BBB room. Please try again later.'))
        except etree.XMLSyntaxError as xml_error:
            response = requests.get(request_url)
            response.raise_for_status()

        # Return an ir.actions.act_url action to open the URL in a new tab
        return {
            'type': 'ir.actions.act_url',
            'url': request_url,
            'target': 'new',
        }

    # function end meeting
    def end_bigbluebutton_meeting(self):
        base_url = "http://test-install.blindsidenetworks.com/bigbluebutton/api/end"
        meeting_id = self.meeting_id  # Retrieve the stored meeting ID
        print('ma b3d al b5ed5 ==>', meeting_id)
        params = {
            'meetingID': meeting_id,
        }

        shared_secret = '8cd8ef52e8e101574e400365b55e11a6'

        call = 'end'

        query_string = urllib.parse.urlencode(params)
        concatenated_string = call + query_string + shared_secret
        checksum = hashlib.sha1(concatenated_string.encode('utf-8')).hexdigest()
        print('end checksum==>', checksum)
        params['checksum'] = checksum

        request_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        print('end request_url==>', request_url)
        response = requests.post(request_url)
        print('endend', response.content)

        try:
            response = requests.post(request_url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.error(f'Error when ending BBB meeting: {str(e)}')
            raise UserError(_('An error occurred when ending the BBB meeting. Please try again later.'))

        return request_url

    # function after end and get info about meeting
    def getMeetingInfo(self):
        base_url = "http://test-install.blindsidenetworks.com/bigbluebutton/api/getMeetingInfo"
        meeting_id = self.meeting_id  # Retrieve the stored meeting ID
        print('b6e5 info ==>', meeting_id)
        params = {
            'meetingID': meeting_id,
        }

        shared_secret = '8cd8ef52e8e101574e400365b55e11a6'

        call = 'getMeetingInfo'

        query_string = urllib.parse.urlencode(params)
        concatenated_string = call + query_string + shared_secret
        checksum = hashlib.sha1(concatenated_string.encode('utf-8')).hexdigest()
        print('getMeetingInfo checksum==>', checksum)
        params['checksum'] = checksum

        request_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        print('getMeetingInfo request_url==>', request_url)
        response = requests.get(request_url)
        print('getMeetingInfo response', response.content)

        try:
            response_xml = etree.fromstring(response.content)
            return_code = response_xml.findtext('returncode')
            if return_code == 'FAILED':
                message_key = response_xml.findtext('messageKey')
                if message_key == 'notFound':
                    raise UserError(_('The meeting has ended.'))
                else:
                    raise UserError(_('An error occurred when joining the BBB room. Please try again later.'))
        except etree.XMLSyntaxError as xml_error:
            response = requests.get(request_url)
            response.raise_for_status()
        return {
            'type': 'ir.actions.act_url',
            'url': request_url,
            'target': 'new',
        }

    # function after end and get info about meeting
    def getMeetings(self):
        base_url = "http://test-install.blindsidenetworks.com/bigbluebutton/api/getMeetings"
        meeting_id = self.meeting_id  # Retrieve the stored meeting ID
        print('getMeetings info ==>', meeting_id)
        params = {
        }

        shared_secret = '8cd8ef52e8e101574e400365b55e11a6'

        call = 'getMeetings'

        query_string = urllib.parse.urlencode(params)
        concatenated_string = call + query_string + shared_secret
        checksum = hashlib.sha1(concatenated_string.encode('utf-8')).hexdigest()
        print('getMeetings checksum==>', checksum)
        params['checksum'] = checksum

        request_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        print('getMeetings request_url==>', request_url)
        response = requests.post(request_url)
        print('getMeetings response', response.content)

        try:
            response = requests.get(request_url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.error(f'Error when ending BBB meeting: {str(e)}')
            raise UserError(_('An error occurred when ending the BBB meeting. Please try again later.'))

        return {
            'type': 'ir.actions.act_url',
            'url': request_url,
            'target': 'new',
        }

    # function for inserting a document into a meeting
    def insert_document(self, meeting_id, xml_string):
        base_url = "http://test-install.blindsidenetworks.com/bigbluebutton/api/insertDocument"

        params = {
            'meetingID': meeting_id,
        }
        print('okok=>', xml_string)

        headers = {
            'Content-Type': 'application/xml'
        }
        shared_secret = '8cd8ef52e8e101574e400365b55e11a6'

        call = 'insertDocument'

        query_string = urllib.parse.urlencode(params)
        concatenated_string = call + query_string + shared_secret
        checksum = hashlib.sha1(concatenated_string.encode('utf-8')).hexdigest()
        print('insertDocument checksum==>', checksum)
        params['checksum'] = checksum

        url = f"{base_url}?{urllib.parse.urlencode(params)}"  # Include params in the URL
        print('url', url)
        response = requests.post(url, headers=headers, data=xml_string)  # Send the XML payload in the request body
        print('print(response.content)', response.content)
        if response.status_code == 200:
            print("Document inserted successfully")
        else:
            print("Failed to insert document")
            print(response.content)

    # function for upload bdf
    def upload_and_send_to_bbb(self):
        # Get the uploaded PDF file content
        pdf_content = self.pdf_file

        # Convert the file content to base64
        base64_content = base64.b64encode(pdf_content).decode('utf-8')
        # base64_content = base64.b64encode(pdf_content).decode('utf-8')  # For Python 3
        meeting_id = self.meeting_id  # Retrieve the stored meeting ID
        # Prepare the XML string with the base64 encoded document
        xml_string = f'''
        <modules>
           <module name="presentation">
                <document current="true" downloadable="true" url="{'https://www.google.com/'}" filename="sample.pdf"/>
                <document removable="false" name="sample.pdf">
                  {base64_content}
                </document>
           </module>
        </modules>
        '''

        # Call the insert_document method with the meeting ID and XML content
        self.insert_document(meeting_id, xml_string)

    # function for check isMeetingRunning
    def isMeetingRunning(self):
        base_url = "http://test-install.blindsidenetworks.com/bigbluebutton/api/isMeetingRunning"
        meeting_id = self.meeting_id  # Retrieve the stored meeting ID
        print('isMeetingRunning info ==>', meeting_id)
        params = {
            'meetingID': meeting_id,
        }

        shared_secret = '8cd8ef52e8e101574e400365b55e11a6'

        call = 'isMeetingRunning'

        query_string = urllib.parse.urlencode(params)
        concatenated_string = call + query_string + shared_secret
        checksum = hashlib.sha1(concatenated_string.encode('utf-8')).hexdigest()
        print('isMeetingRunning checksum==>', checksum)
        params['checksum'] = checksum

        request_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        print('isMeetingRunning request_url==>', request_url)
        response = requests.get(request_url)
        print('isMeetingRunning response', response.content)

        try:
            response = requests.get(request_url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.error(f'Error when isMeetingRunning BBB meeting: {str(e)}')
            raise UserError(_('An error occurred when ending the BBB meeting. Please try again later.'))

        return {
            'type': 'ir.actions.act_url',
            'url': request_url,
            'target': 'new',
        }

    # function for check getRecordings
    def getRecordings(self):
        base_url = "http://test-install.blindsidenetworks.com/bigbluebutton/api/getRecordings"
        meeting_id = self.meeting_id  # Retrieve the stored meeting ID
        print('getRecordings info ==>', meeting_id)
        params = {
            'meetingID': meeting_id,
        }

        shared_secret = '8cd8ef52e8e101574e400365b55e11a6'

        call = 'getRecordings'

        query_string = urllib.parse.urlencode(params)
        concatenated_string = call + query_string + shared_secret
        checksum = hashlib.sha1(concatenated_string.encode('utf-8')).hexdigest()
        print('getRecordings checksum==>', checksum)
        params['checksum'] = checksum

        request_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        print('getRecordings request_url==>', request_url)
        response = requests.get(request_url)
        print('getRecordings response', response.content)

        try:
            response_xml = etree.fromstring(response.content)
            recording_tags = response_xml.findall('.//recording')
            if len(recording_tags) == 0:
                raise UserError(_('There are no recordings for the meeting(s).'))
            else:
                self.record_id = recording_tags[0].findtext('recordID')
                print("recordID==>", recording_tags[0].findtext('recordID'))
        except etree.XMLSyntaxError as xml_error:
            raise UserError(_('An error occurred when parsing the XML response from the server.'))

        return {
            'type': 'ir.actions.act_url',
            'url': request_url,
            'target': 'new',
        }

    # function for check publishRecordings
    def publishRecordings(self):
        base_url = "http://test-install.blindsidenetworks.com/bigbluebutton/api/publishRecordings"
        meeting_id = self.meeting_id  # Retrieve the stored meeting ID
        record_id = self.record_id  # Retrieve the stored meeting ID
        print('publishRecordings info ==>', meeting_id)
        params = {
            'recordID': record_id,
            'publish': 'true',
        }

        shared_secret = '8cd8ef52e8e101574e400365b55e11a6'

        call = 'publishRecordings'

        query_string = urllib.parse.urlencode(params)
        concatenated_string = call + query_string + shared_secret
        checksum = hashlib.sha1(concatenated_string.encode('utf-8')).hexdigest()
        print('publishRecordings checksum==>', checksum)
        params['checksum'] = checksum

        request_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        print('publishRecordings request_url==>', request_url)
        response = requests.post(request_url)
        print('publishRecordings response', response.content)

        try:
            response = requests.post(request_url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.error(f'Error when ending BBB meeting: {str(e)}')
            raise UserError(_('An error occurred when ending the BBB meeting. Please try again later.'))

        return {
            'type': 'ir.actions.act_url',
            'url': request_url,
            'target': 'new',
        }

    # function for check deleteRecordings
    def deleteRecordings(self):
        base_url = "http://test-install.blindsidenetworks.com/bigbluebutton/api/deleteRecordings"
        meeting_id = self.meeting_id  # Retrieve the stored meeting ID
        record_id = self.record_id  # Retrieve the stored record ID
        print('deleteRecordings info ==>', record_id)
        params = {
            'recordID': record_id,
        }

        shared_secret = '8cd8ef52e8e101574e400365b55e11a6'

        call = 'deleteRecordings'

        query_string = urllib.parse.urlencode(params)
        concatenated_string = call + query_string + shared_secret
        checksum = hashlib.sha1(concatenated_string.encode('utf-8')).hexdigest()
        print('deleteRecordings checksum==>', checksum)
        params['checksum'] = checksum

        request_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        print('deleteRecordings request_url==>', request_url)
        response = requests.delete(request_url)
        print('deleteRecordings response', response.content)

        # if response.content.strip() == b'':
        #     response.raise_for_status()
        #     raise UserError(_('Record deleted.'))
        # else:
        #     try:
        #         response.raise_for_status()
        #     except requests.exceptions.RequestException as e:
        #         _logger.error(f'Error when deleting the recording: {str(e)}')
        #         raise UserError(_('An error occurred when deleting the recording. Please try again later.'))


        return {
            'type': 'ir.actions.act_url',
            'url': request_url,
            'target': 'new',
        }

    # function for check getRecordingTextTracks
    def getRecordingTextTracks(self):
        base_url = "http://test-install.blindsidenetworks.com/bigbluebutton/api/getRecordingTextTracks"
        record_id = self.record_id  # Retrieve the stored record ID
        print('getRecordingTextTracks info ==>', record_id)
        params = {
            'recordID': record_id,
        }

        shared_secret = '8cd8ef52e8e101574e400365b55e11a6'

        call = 'getRecordingTextTracks'

        query_string = urllib.parse.urlencode(params)
        concatenated_string = call + query_string + shared_secret
        checksum = hashlib.sha1(concatenated_string.encode('utf-8')).hexdigest()
        print('getRecordingTextTracks checksum==>', checksum)
        params['checksum'] = checksum

        request_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        print('getRecordingTextTracks request_url==>', request_url)
        response = requests.get(request_url)
        print('getRecordingTextTracks response', response.content)

        try:
            response = requests.get(request_url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.error(f'Error when isMeetingRunning BBB meeting: {str(e)}')
            raise UserError(_('An error occurred when ending the BBB meeting. Please try again later.'))

        # Process the response and handle accordingly

        return {
            'type': 'ir.actions.act_url',
            'url': request_url,
            'target': 'new',
        }
