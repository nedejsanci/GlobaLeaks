# -*- coding: utf-8 -*-
#
# Handlers dealing with custodian user functionalities
from globaleaks import models
from globaleaks.handlers.admin.context import admin_serialize_context
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.user import user_serialize_user
from globaleaks.models import serializers
from globaleaks.orm import transact
from globaleaks.rest import requests
from globaleaks.utils.templating import Templating
from globaleaks.utils.utility import datetime_now


@transact
def get_identityaccessrequest_list(session, tid):
    return [serializers.serialize_identityaccessrequest(session, iar)
        for iar in session.query(models.IdentityAccessRequest).filter(models.IdentityAccessRequest.receivertip_id == models.ReceiverTip.id,
                                                                      models.ReceiverTip.internaltip_id == models.InternalTip.id,
                                                                      models.InternalTip.tid == tid)]


@transact
def get_identityaccessrequest(session, tid, identityaccessrequest_id):
    iar = session.query(models.IdentityAccessRequest) \
               .filter(models.IdentityAccessRequest.id == identityaccessrequest_id,
                       models.IdentityAccessRequest.receivertip_id == models.ReceiverTip.id,
                       models.ReceiverTip.internaltip_id == models.InternalTip.id,
                       models.InternalTip.tid == tid).one()

    return serializers.serialize_identityaccessrequest(session, iar)


def db_create_identity_access_reply_notifications(session, itip, rtip, iar):
    """
    Transaction for the creation of notifications related to identity access replies
    :param session: An ORM session
    :param itip: A itip ID of the tip involved in the request
    :param rtip: A rtip ID of the rtip involved in the request
    :param iar: A identity access request model
    """
    for user in session.query(models.User) \
                       .filter(models.User.id == rtip.receiver_id,
                               models.User.notification.is_(True)):
        context = session.query(models.Context).filter(models.Context.id == itip.context_id).one()

        data = {
            'type': 'identity_access_authorized' if iar.reply == 'authorized' else 'identity_access_denied'
        }

        data['user'] = user_serialize_user(session, user, user.language)
        data['tip'] = serializers.serialize_rtip(session, itip, rtip, user.language)
        data['context'] = admin_serialize_context(session, context, user.language)
        data['iar'] = serializers.serialize_identityaccessrequest(session, iar)
        data['node'] = db_admin_serialize_node(session, user.tid, user.language)

        if data['node']['mode'] == 'default':
            data['notification'] = db_get_notification(session, user.tid, user.language)
        else:
            data['notification'] = db_get_notification(session, 1, user.language)

        subject, body = Templating().get_mail_subject_and_body(data)

        session.add(models.Mail({
            'address': data['user']['mail_address'],
            'subject': subject,
            'body': body,
            'tid': user.tid
        }))


@transact
def update_identityaccessrequest(session, tid, user_id, identityaccessrequest_id, request):
    iar, rtip, itip = session.query(models.IdentityAccessRequest, models.ReceiverTip, models.InternalTip) \
                             .filter(models.IdentityAccessRequest.id == identityaccessrequest_id,
                                     models.ReceiverTip.id == models.IdentityAccessRequest.receivertip_id,
                                     models.ReceiverTip.internaltip_id == models.InternalTip.id,
                                     models.InternalTip.tid == tid).one()

    if iar.reply == 'pending':
        iar.reply_date = datetime_now()
        iar.reply_user_id = user_id
        iar.reply = request['reply']
        iar.reply_motivation = request['reply_motivation']

        if iar.reply == 'authorized':
            rtip.can_access_whistleblower_identity = True

        db_create_identity_access_reply_notifications(session, itip, rtip, iar)

    return serializers.serialize_identityaccessrequest(session, iar)


class IdentityAccessRequestInstance(BaseHandler):
    """
    This handler allow custodians to manage an identity access request by a receiver
    """
    check_roles = 'custodian'

    def get(self, identityaccessrequest_id):
        return get_identityaccessrequest(self.request.tid, identityaccessrequest_id)

    def put(self, identityaccessrequest_id):
        request = self.validate_message(self.request.content.read(), requests.CustodianIdentityAccessRequestDesc)

        return update_identityaccessrequest(self.request.tid,
                                            self.session.user_id,
                                            identityaccessrequest_id,
                                            request)


class IdentityAccessRequestsCollection(BaseHandler):
    """
    This handler allow custodians to manage an identity access request by a receiver
    """
    check_roles = 'custodian'

    def get(self):
        return get_identityaccessrequest_list(self.request.tid)
