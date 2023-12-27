from odoo import api,models,fields

class AccMailThread(models.AbstractModel):
	_inherit = "mail.thread"

	@api.returns('mail.message', lambda value: value.id)
	def message_post(self, *,
					 body='', subject=None, message_type='notification',
					 email_from=None, author_id=None, parent_id=False,
					 subtype_xmlid=None, subtype_id=False, partner_ids=None, channel_ids=None,
					 attachments=None, attachment_ids=None,
					 add_sign=True, record_name=False, email_to=None, email_cc=None,
					 **kwargs):
		""" Post a new message in an existing thread, returning the new
			mail.message ID.
			:param str body: body of the message, usually raw HTML that will
				be sanitized
			:param str subject: subject of the message
			:param str message_type: see mail_message.message_type field. Can be anything but 
				user_notification, reserved for message_notify
			:param int parent_id: handle thread formation
			:param int subtype_id: subtype_id of the message, mainly use fore
				followers mechanism
			:param list(int) partner_ids: partner_ids to notify
			:param list(int) channel_ids: channel_ids to notify
			:param list(tuple(str,str), tuple(str,str, dict) or int) attachments : list of attachment tuples in the form
				``(name,content)`` or ``(name,content, info)``, where content is NOT base64 encoded
			:param list id attachment_ids: list of existing attachement to link to this message
				-Should only be setted by chatter
				-Attachement object attached to mail.compose.message(0) will be attached
					to the related document.
			Extra keyword arguments will be used as default column values for the
			new mail.message record.
			:return int: ID of newly created mail.message
		"""
		self.ensure_one()  # should always be posted on a record, use message_notify if no record
		# split message additional values from notify additional values
		msg_kwargs = dict((key, val) for key, val in kwargs.items() if key in self.env['mail.message']._fields)
		notif_kwargs = dict((key, val) for key, val in kwargs.items() if key not in msg_kwargs)

		if self._name == 'mail.thread' or not self.id or message_type == 'user_notification':
			raise ValueError('message_post should only be call to post message on record. Use message_notify instead')

		if 'model' in msg_kwargs or 'res_id' in msg_kwargs:
			raise ValueError("message_post doesn't support model and res_id parameters anymore. Please call message_post on record.")
		if 'subtype' in kwargs:
			raise ValueError("message_post doesn't support subtype parameter anymore. Please give a valid subtype_id or subtype_xmlid value instead.")

		self = self._fallback_lang() # add lang to context imediatly since it will be usefull in various flows latter.

		# Explicit access rights check, because display_name is computed as sudo.
		self.check_access_rights('read')
		self.check_access_rule('read')
		record_name = record_name or self.display_name

		partner_ids = set(partner_ids or [])
		channel_ids = set(channel_ids or [])

		if any(not isinstance(pc_id, int) for pc_id in partner_ids | channel_ids):
			raise ValueError('message_post partner_ids and channel_ids must be integer list, not commands')

		# Find the message's author
		author_id, email_from = self._message_compute_author(author_id, email_from, raise_exception=True)

		if subtype_xmlid:
			subtype_id = self.env['ir.model.data'].xmlid_to_res_id(subtype_xmlid)
		if not subtype_id:
			subtype_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note')

		# automatically subscribe recipients if asked to
		if self._context.get('mail_post_autofollow') and partner_ids:
			self.message_subscribe(list(partner_ids))

		MailMessage_sudo = self.env['mail.message'].sudo()
		if self._mail_flat_thread and not parent_id:
			parent_message = MailMessage_sudo.search([('res_id', '=', self.id), ('model', '=', self._name), ('message_type', '!=', 'user_notification')], order="id ASC", limit=1)
			# parent_message searched in sudo for performance, only used for id.
			# Note that with sudo we will match message with internal subtypes.
			parent_id = parent_message.id if parent_message else False
		elif parent_id:
			old_parent_id = parent_id
			parent_message = MailMessage_sudo.search([('id', '=', parent_id), ('parent_id', '!=', False)], limit=1)
			# avoid loops when finding ancestors
			processed_list = []
			if parent_message:
				new_parent_id = parent_message.parent_id and parent_message.parent_id.id
				while (new_parent_id and new_parent_id not in processed_list):
					processed_list.append(new_parent_id)
					parent_message = parent_message.parent_id
				parent_id = parent_message.id

		values = dict(msg_kwargs)
		values.update({
			'author_id': author_id,
			'email_from': email_from,
			'model': self._name,
			'res_id': self.id,
			'body': body,
			'subject': subject or False,
			'message_type': message_type,
			'parent_id': parent_id,
			'subtype_id': subtype_id,
			'partner_ids': partner_ids,
			'channel_ids': channel_ids,
			'add_sign': add_sign,
			'record_name': record_name,
			'email_to':email_to,
			'email_cc':email_cc,`
		})
		attachments = attachments or []
		attachment_ids = attachment_ids or []
		attachement_values = self._message_post_process_attachments(attachments, attachment_ids, values)
		values.update(attachement_values)  # attachement_ids, [body]

		new_message = self._message_create(values)

		# Set main attachment field if necessary
		self._message_set_main_attachment_id(values['attachment_ids'])

		if values['author_id'] and values['message_type'] != 'notification' and not self._context.get('mail_create_nosubscribe'):
			if self.env['res.partner'].browse(values['author_id']).active:  # we dont want to add odoobot/inactive as a follower
				self._message_subscribe([values['author_id']])

		self._message_post_after_hook(new_message, values)
		self._notify_thread(new_message, values, **notif_kwargs)
		return new_message

class AccMailComposeMessage(models.TransientModel):
	_inherit = "mail.compose.message"

	email_to = fields.Char("Email To")
	email_cc = fields.Char("Email cc")

	def get_mail_values(self, res_ids):
		"""Generate the values that will be used by send_mail to create mail_messages
		or mail_mails. """
		self.ensure_one()
		results = dict.fromkeys(res_ids, False)
		rendered_values = {}
		mass_mail_mode = self.composition_mode == 'mass_mail'

		# render all template-based value at once
		if mass_mail_mode and self.model:
			rendered_values = self.render_message(res_ids)
		# compute alias-based reply-to in batch
		reply_to_value = dict.fromkeys(res_ids, None)
		if mass_mail_mode and not self.no_auto_thread:
			records = self.env[self.model].browse(res_ids)
			reply_to_value = records._notify_get_reply_to(default=self.email_from)

		blacklisted_rec_ids = set()
		if mass_mail_mode and issubclass(type(self.env[self.model]), self.pool['mail.thread.blacklist']):
			self.env['mail.blacklist'].flush(['email'])
			self._cr.execute("SELECT email FROM mail_blacklist WHERE active=true")
			blacklist = {x[0] for x in self._cr.fetchall()}
			if blacklist:
				targets = self.env[self.model].browse(res_ids).read(['email_normalized'])
				# First extract email from recipient before comparing with blacklist
				blacklisted_rec_ids.update(target['id'] for target in targets
										   if target['email_normalized'] in blacklist)

		for res_id in res_ids:
			# static wizard (mail.message) values
			mail_values = {
				'subject': self.subject,
				'body': self.body or '',
				'parent_id': self.parent_id and self.parent_id.id,
				'partner_ids': [partner.id for partner in self.partner_ids],
				'attachment_ids': [attach.id for attach in self.attachment_ids],
				'author_id': self.author_id.id,
				'email_from': self.email_from,
				'email_to': self.email_to,
				'email_cc': self.email_cc,
				'record_name': self.record_name,
				'no_auto_thread': self.no_auto_thread,
				'mail_server_id': self.mail_server_id.id,
				'mail_activity_type_id': self.mail_activity_type_id.id,
			}

			# mass mailing: rendering override wizard static values
			if mass_mail_mode and self.model:
				record = self.env[self.model].browse(res_id)
				mail_values['headers'] = record._notify_email_headers()
				# keep a copy unless specifically requested, reset record name (avoid browsing records)
				mail_values.update(notification=not self.auto_delete_message, model=self.model, res_id=res_id, record_name=False)
				# auto deletion of mail_mail
				if self.auto_delete or self.template_id.auto_delete:
					mail_values['auto_delete'] = True
				# rendered values using template
				email_dict = rendered_values[res_id]
				mail_values['partner_ids'] += email_dict.pop('partner_ids', [])
				mail_values.update(email_dict)
				if not self.no_auto_thread:
					mail_values.pop('reply_to')
					if reply_to_value.get(res_id):
						mail_values['reply_to'] = reply_to_value[res_id]
				if self.no_auto_thread and not mail_values.get('reply_to'):
					mail_values['reply_to'] = mail_values['email_from']
				# mail_mail values: body -> body_html, partner_ids -> recipient_ids
				mail_values['body_html'] = mail_values.get('body', '')
				mail_values['recipient_ids'] = [(4, id) for id in mail_values.pop('partner_ids', [])]

				# process attachments: should not be encoded before being processed by message_post / mail_mail create
				mail_values['attachments'] = [(name, base64.b64decode(enc_cont)) for name, enc_cont in email_dict.pop('attachments', list())]
				attachment_ids = []
				for attach_id in mail_values.pop('attachment_ids'):
					new_attach_id = self.env['ir.attachment'].browse(attach_id).copy({'res_model': self._name, 'res_id': self.id})
					attachment_ids.append(new_attach_id.id)
				attachment_ids.reverse()
				mail_values['attachment_ids'] = self.env['mail.thread'].with_context(attached_to=record)._message_post_process_attachments(
					mail_values.pop('attachments', []),
					attachment_ids,
					{'model': 'mail.message', 'res_id': 0}
				)['attachment_ids']
				# Filter out the blacklisted records by setting the mail state to cancel -> Used for Mass Mailing stats
				if res_id in blacklisted_rec_ids:
					mail_values['state'] = 'cancel'
					# Do not post the mail into the recipient's chatter
					mail_values['notification'] = False

			results[res_id] = mail_values
		return results
