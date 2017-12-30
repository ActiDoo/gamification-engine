import random
import threading

import os
from sqlalchemy.sql.expression import and_, select
from sqlalchemy.sql.functions import func

from gengine.app.model import t_subject_device, t_subject_messages
from gengine.base.model import update_connection
from gengine.base.settings import get_settings
from gengine.base.util import lstrip_word
from gengine.metadata import DBSession

threadlocal = threading.local()

import logging
log = logging.getLogger(__name__)

try:
    from apns import APNs, Payload
except ImportError as e:
    log.info("tapns3 not installed")

try:
    from gcm import GCM
except ImportError as e:
    log.info("python-gcm not installed")


def get_prod_apns():
    """
    http://stackoverflow.com/questions/1762555/creating-pem-file-for-apns

    Step 1: Create Certificate .pem from Certificate .p12
    Command: openssl pkcs12 -clcerts -nokeys -out apns-dev-cert.pem -in apns-dev-cert.p12

    Step 2: Create Key .pem from Key .p12
    Command : openssl pkcs12 -nocerts -out apns-dev-key.pem -in apns-dev-key.p12

    Step 3: If you want to remove pass phrase asked in second step
    Command : openssl rsa -in apns-dev-key.pem -out apns-dev-key-noenc.pem

    """
    if not hasattr(threadlocal, "prod_apns"):
        settings = get_settings()
        cert_file = os.environ.get("APNS_CERT", settings.get("apns.prod.certificate"))
        key_file = os.environ.get("APNS_KEY", settings.get("apns.prod.key"))
        sandbox = False  # other_helpers.boolify(os.environ.get("APNS_SANDBOX",settings.get("apns.sandbox")))
        threadlocal.prod_apns = APNs(use_sandbox=sandbox, cert_file=cert_file, key_file=key_file, enhanced=True)

        def response_listener(error_response):
            log.debug("client get error-response: " + str(error_response))

        threadlocal.prod_apns.gateway_server.register_response_listener(response_listener)
    return threadlocal.prod_apns

def get_dev_apns():
    """
    http://stackoverflow.com/questions/1762555/creating-pem-file-for-apns

    Step 1: Create Certificate .pem from Certificate .p12
    Command: openssl pkcs12 -clcerts -nokeys -out apns-dev-cert.pem -in apns-dev-cert.p12

    Step 2: Create Key .pem from Key .p12
    Command : openssl pkcs12 -nocerts -out apns-dev-key.pem -in apns-dev-key.p12

    Step 3: If you want to remove pass phrase asked in second step
    Command : openssl rsa -in apns-dev-key.pem -out apns-dev-key-noenc.pem

    """
    if not hasattr(threadlocal, "dev_apns"):
        settings = get_settings()
        cert_file = os.environ.get("APNS_CERT", settings.get("apns.dev.certificate"))
        key_file = os.environ.get("APNS_KEY", settings.get("apns.dev.key"))
        sandbox = True  # other_helpers.boolify(os.environ.get("APNS_SANDBOX",settings.get("apns.sandbox")))
        threadlocal.dev_apns = APNs(use_sandbox=sandbox, cert_file=cert_file, key_file=key_file, enhanced=True)

        def response_listener(error_response):
            log.debug("client get error-response: " + str(error_response))

        threadlocal.dev_apns.gateway_server.register_response_listener(response_listener)
    return threadlocal.dev_apns

def get_gcm():
    if not hasattr(threadlocal, "gcm"):
        settings = get_settings()
        # JSON request
        API_KEY = os.environ.get("GCM_API_KEY", settings.get("gcm.api_key"))
        threadlocal.gcm = GCM(API_KEY)
    return threadlocal.gcm

def prod_apns_feedback():
    apns_feedback(get_prod_apns(), "prod_")

def dev_apns_feedback():
    apns_feedback(get_dev_apns(), "dev_")

def apns_feedback(apns, prefix):
    # Get feedback messages.
    uS = update_connection()

    for (token_hex, fail_time) in apns.feedback_server.items():
        try:
            if not isinstance(token_hex, str):
                token_hex = token_hex.decode("utf8")

            token_hex = prefix + token_hex

            log.debug("APNS Feedback Entry: %s", token_hex + "_" + str(fail_time))

            # do stuff with token_hex and fail_time
            q = t_subject_device.select().where(t_subject_device.c.push_id==token_hex)
            rows = uS.execute(q).fetchall()

            for device in rows:
                log.debug("APNSPushID found in Database: %s", token_hex)
                if fail_time > device["registered"]:
                    log.debug("Fail-Time is before Registered-At")
                    uS.execute(t_subject_device.delete().where(
                        t_subject_device.c.device_id == device["device_id"],
                        t_subject_device.c.subject_id == device["subject_id_id"],
                    ))
        except:
            log.exception("Processing APNS Feedback failed for an entry.")


def gcm_feedback(response):
    # Successfully handled registration_ids
    if 'success' in response:
        for reg_id, success_id in response['success'].items():
            log.debug('Successfully sent notification for reg_id {0}'.format(reg_id))


    # Handling errors
    if 'errors' in response:

        for error, reg_ids in response['errors'].items():
            # Check for errors and act accordingly
            if error in ['NotRegistered', 'InvalidRegistration']:
                # Remove reg_ids from database
                for reg_id in reg_ids:
                    q = t_subject_device.delete().where(t_subject_device.c.push_id == reg_id)
                    DBSession.execute(q)

    # Repace reg_id with canonical_id in your database
    if 'canonical' in response:
        for reg_id, canonical_id in response['canonical'].items():
            if not isinstance(reg_id, str):
                reg_id = reg_id.decode("utf8")

            log.debug("Replacing reg_id: {0} with canonical_id: {1} in db".format(reg_id, canonical_id))

            q = t_subject_device.update().values({
                "push_id" : canonical_id
            }).where(t_subject_device.c.push_id == reg_id)

            DBSession.execute(q)

    DBSession.flush()

def send_push_message(
        subject_id,
        text="",
        custom_payload={},
        title="Gamification-Engine",
        android_text=None,
        ios_text=None):

    message_count = DBSession.execute(select([func.count("*").label("c")],from_obj=t_subject_messages).where(and_(
        t_subject_messages.c.subject_id == subject_id,
        t_subject_messages.c.is_read == False
    ))).scalar()

    data = dict({"title": title,
                 "badge": message_count}, **custom_payload)

    settings = get_settings()

    if not ios_text:
        ios_text = text

    if not android_text:
        android_text = text

    rows = DBSession.execute(select([t_subject_device.c.push_id, t_subject_device.c.device_os], from_obj=t_subject_device).distinct().where(t_subject_device.c.subject_id==subject_id)).fetchall()

    for device in rows:

        if "ios" in device.device_os.lower():
            identifier = random.getrandbits(32)

            if custom_payload:
                payload = Payload(alert=ios_text, custom=data, badge=message_count, sound="default")
            else:
                payload = Payload(alert=ios_text, custom=data, badge=message_count, sound="default")

            log.debug("Sending Push message to User (ID: %s)", subject_id)

            if device.push_id.startswith("prod_"):
                get_prod_apns().gateway_server.send_notification(device.push_id[5:], payload, identifier=identifier)
            elif device.push_id.startswith("dev_"):
                get_dev_apns().gateway_server.send_notification(device.push_id[4:], payload, identifier=identifier)

        if "android" in device.device_os.lower():

            log.debug("Sending Push message to User (ID: %s)", subject_id)
            push_id = lstrip_word(device.push_id, "dev_")
            push_id = lstrip_word(push_id, "prod_")

            response = get_gcm().json_request(registration_ids=[push_id, ],
                                              data={"message": android_text, "data": data, "title": title},
                                              restricted_package_name=os.environ.get("GCM_PACKAGE", settings.get("gcm.package","")),
                                              priority='high',
                                              delay_while_idle=False)
            if response:
                gcm_feedback(response)