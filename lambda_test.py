import json
import logging
import os
from openedx_rest_api_client import client as openedx_client
from functools import reduce

logger = logging.getLogger()
logger.setLevel(int(os.environ.get("LOGGING_LEVEL", logging.INFO)))

LMS_CLIENT_ID = os.environ.get('LMS_CLIENT_ID')
LMS_CLIENT_SECRET = os.environ.get('LMS_CLIENT_SECRET')
LMS_URL = os.environ.get('LMS_URL')

HUBSPOT_TOKEN = os.environ.get('HUBSPOT_TOKEN')

lms_client = openedx_client.OpenedxRESTAPIClient(
    base_url=LMS_URL, client_id=LMS_CLIENT_ID, client_secret=LMS_CLIENT_SECRET)


def lambda_handler(event, context):
    """
    Handle webhooks and filters coming from Hubspot.

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """

    logger.info(f"Event: {json.dumps(event)}")

    body_str = event.get('body')
    if body_str:
        try:
            body = json.loads(body_str)
        except json.JSONDecodeError as e:
            message = f"JSON Decode Error '{e.msg}' loading '{e.doc}' in position {e.pos}"
            logger.error(message)
            return {
                'status_code': 406,
                'message': message
            }

    else:
        message = "No body in event"
        logger.error(message)
        return {
            'status_code': 406,
            'message': message
        }

    email = body.get('email')
    first_name = body.get('First_Name')
    last_name = body.get('Last_name')
    full_name = ' '.join([first_name, last_name])
    course_id = body.get('Course_Id')
    password = str(body.get('Password'))

    messages = []

    # initially take the user name as the first word of the first name.
    username = first_name.split(' ')[0]

    logger.info(f"Registering {full_name} ({email}) with password {password} and enrolling into {course_id}.")

    # Create a client to make API calls
    lms_client = openedx_client.OpenedxRESTAPIClient(
        base_url=LMS_URL, client_id=LMS_CLIENT_ID, client_secret=LMS_CLIENT_SECRET)

    # Validate the data
    validation_result = lms_client.validation_registration(
        email=email,
        username=username,
        name=full_name,
        password=password,
    )

    validation_decisions = validation_result.get('validation_decisions', {})

    if not validation_decisions:
        return {
            'status_code': 400,
            'validation_result': validation_result
        }

    # Check if the user exists. In this case, don't stop, just don't register and continue
    user_exists = validation_decisions.get('email', "") == f"It looks like {email} belongs to an existing account. Try again with a different email address."
    if user_exists:
        message = f"User with email {email} already exists. Skipping registration."
        logger.warning(message)
        messages.append(message)
    else:
        # If the user does not exist, register it.

        # First check if the form is valid in the other fields, except username errors (handled separately)
        form_is_valid = not bool(reduce(lambda a, b: a+b, [v for k, v in validation_decisions.items() if k != 'username'], ''))

        if not form_is_valid:
            message = (f"Error validating data for {email}. "
                       f"{'. '.join([k + ': ' + v for k,v in validation_decisions.items() if v])}")
            logger.error(message)
            return {
                "statusCode": 422,
                "validation_errors": message,
            }

        logger.info("Form is valid.")

        # Handle errors in username, replace by one of the suggestions
        if validation_decisions.get('username') == (f"It looks like {username} belongs to an existing account. "
                                                    f"Try again with a different username."):
            username_suggestions = validation_result.get('username_suggestions')
            message = (f"Invalid username '{username}': '{validation_decisions.get('username')}'. "
                       f"Replacing by '{username_suggestions[0]}'")
            logger.warning(message)
            username = username_suggestions[0]
            messages.append(message)

        # Handle other type of username errors
        elif validation_decisions.get('username'):

            message = f"Error validating data for {email}. username: {validation_decisions.get('username')}"
            return {
                'status_code': 422,
                'validation_errors': message
            }

        # Register the user
        registration_result = lms_client.register_account(
            email=email,
            username=username,
            name=full_name,
            password=password,
            course_id=course_id,
            terms_of_service='true',
        )

        if not registration_result.get('success'):
            error_message = {
                k: v[0].get('user_message')
                for k, v in registration_result.items()
                if k not in {'error_code', 'username_suggestions'}
            }
            message = f"Error registering {email}. {'. '.join([k + ': ' + v for k,v in error_message.items()])}"
            logger.error(message)
            return {
                "statusCode": 422,
                "message": message,
            }
        else:
            message = f"Successfully registered {full_name} ({email}) with password {password} and username '{username}'."
            logger.info(message)
            messages.append(message)

    lms_client2 = openedx_client.OpenedxRESTAPIClient(
        base_url=LMS_URL, client_id=LMS_CLIENT_ID, client_secret=LMS_CLIENT_SECRET)

    # Enroll the user in the course
    enrollment_result = lms_client2.change_enrollment(
        emails=[email],
        courses=[course_id],
        action='unenroll',
        email_students=False,
    )

    if 'detail' in enrollment_result:
        error_message = enrollment_result.get('detail')
        logger.error(f"Error enrolling {email} in {course_id}: {error_message}")
        return {
            "statusCode": 422,
            "message": error_message,
        }
    elif 'status_code' in enrollment_result:
        error_message = enrollment_result.get('response')
        logger.error(f"Error {enrollment_result.get('status_code')} enrolling {email} in {course_id}: {error_message}")
        return {
            "statusCode": enrollment_result.get('status_code'),
            "message": error_message,
        }
    else:
        message = f"Successfully enrolled {email} in course {course_id}."
        logger.info(message)
        messages.append(message)

    return {
        "statusCode": 200,
        "messages": messages
    }

event = {
  "resource": "/hubspot_webhook",
  "path": "/hubspot_webhook/",
  "httpMethod": "POST",
  "headers": {
    "Accept": "application/json",
    "CloudFront-Forwarded-Proto": "https",
    "CloudFront-Is-Desktop-Viewer": "true",
    "CloudFront-Is-Mobile-Viewer": "false",
    "CloudFront-Is-SmartTV-Viewer": "false",
    "CloudFront-Is-Tablet-Viewer": "false",
    "CloudFront-Viewer-ASN": "14618",
    "CloudFront-Viewer-Country": "US",
    "Content-Type": "application/json",
    "Host": "k5bqz34xfi.execute-api.us-east-1.amazonaws.com",
    "User-Agent": "HubSpot Connect 2.0 (http://dev.hubspot.com/) (namespace: WebhooksPlatformExecution) - WebhooksPlatformService-userweb",
    "Via": "1.1 3c7ef4fe3f4a27b69b8df486fc6210e4.cloudfront.net (CloudFront)",
    "X-Amz-Cf-Id": "l20OhUnGPw627SZwfot7qLrI5pCP69qiOwz8tRKd-uC5LgulKPkdpQ==",
    "X-Amzn-Trace-Id": "Root=1-650b5f81-511c4eff1fc2385739854506",
    "X-Forwarded-For": "54.174.62.149, 130.176.137.73",
    "X-Forwarded-Port": "443",
    "X-Forwarded-Proto": "https",
    "X-HS-Internal-Request": "0",
    "X-HS-Internal-User-Request": "0",
    "X-HS-User-Request": "1",
    "X-HubSpot-Client-IP": "190.229.27.129",
    "X-HubSpot-Correlation-Id": "8b46dac7-c49d-48e0-a634-caa7d539bd84",
    "X-HubSpot-Requesting-Chain-bin": "CpYBChxhdXRvbWF0aW9uLXVpLWNhbnZhc0AxLjM1MDc4EgJVSRpyaHR0cHM6Ly9hcHAuaHVic3BvdC5jb20vd29ya2Zsb3dzLzI4Njk4OTEvcGxhdGZvcm0vZmxvdy80NzE0NDQ0OTQvZWRpdC9hY3Rpb25zL25ldy1hY3Rpb24vd2ViaG9vaz9lZGdlSWQ9NC1lZGdlLTEmEgIIBA==",
    "X-HubSpot-Timeout-Millis": "24988",
    "X-Trace": ""
  },
  "multiValueHeaders": {
    "Accept": [
      "application/json"
    ],
    "CloudFront-Forwarded-Proto": [
      "https"
    ],
    "CloudFront-Is-Desktop-Viewer": [
      "true"
    ],
    "CloudFront-Is-Mobile-Viewer": [
      "false"
    ],
    "CloudFront-Is-SmartTV-Viewer": [
      "false"
    ],
    "CloudFront-Is-Tablet-Viewer": [
      "false"
    ],
    "CloudFront-Viewer-ASN": [
      "14618"
    ],
    "CloudFront-Viewer-Country": [
      "US"
    ],
    "Content-Type": [
      "application/json"
    ],
    "Host": [
      "k5bqz34xfi.execute-api.us-east-1.amazonaws.com"
    ],
    "User-Agent": [
      "HubSpot Connect 2.0 (http://dev.hubspot.com/) (namespace: WebhooksPlatformExecution) - WebhooksPlatformService-userweb"
    ],
    "Via": [
      "1.1 3c7ef4fe3f4a27b69b8df486fc6210e4.cloudfront.net (CloudFront)"
    ],
    "X-Amz-Cf-Id": [
      "l20OhUnGPw627SZwfot7qLrI5pCP69qiOwz8tRKd-uC5LgulKPkdpQ=="
    ],
    "X-Amzn-Trace-Id": [
      "Root=1-650b5f81-511c4eff1fc2385739854506"
    ],
    "X-Forwarded-For": [
      "54.174.62.149, 130.176.137.73"
    ],
    "X-Forwarded-Port": [
      "443"
    ],
    "X-Forwarded-Proto": [
      "https"
    ],
    "X-HS-Internal-Request": [
      "0"
    ],
    "X-HS-Internal-User-Request": [
      "0"
    ],
    "X-HS-User-Request": [
      "1"
    ],
    "X-HubSpot-Client-IP": [
      "190.229.27.129"
    ],
    "X-HubSpot-Correlation-Id": [
      "8b46dac7-c49d-48e0-a634-caa7d539bd84"
    ],
    "X-HubSpot-Requesting-Chain-bin": [
      "CpYBChxhdXRvbWF0aW9uLXVpLWNhbnZhc0AxLjM1MDc4EgJVSRpyaHR0cHM6Ly9hcHAuaHVic3BvdC5jb20vd29ya2Zsb3dzLzI4Njk4OTEvcGxhdGZvcm0vZmxvdy80NzE0NDQ0OTQvZWRpdC9hY3Rpb25zL25ldy1hY3Rpb24vd2ViaG9vaz9lZGdlSWQ9NC1lZGdlLTEmEgIIBA=="
    ],
    "X-HubSpot-Timeout-Millis": [
      "24988"
    ],
    "X-Trace": [
      ""
    ]
  },
  "queryStringParameters": None,
  "multiValueQueryStringParameters": None,
  "pathParameters": None,
  "stageVariables": None,
  "requestContext": {
    "resourceId": "wctzch",
    "resourcePath": "/hubspot_webhook",
    "httpMethod": "POST",
    "extendedRequestId": "LkvcOFxKoAMFj-A=",
    "requestTime": "20/Sep/2023:21:09:21 +0000",
    "path": "/Prod/hubspot_webhook/",
    "accountId": "212507341974",
    "protocol": "HTTP/1.1",
    "stage": "Prod",
    "domainPrefix": "k5bqz34xfi",
    "requestTimeEpoch": 1695244161189,
    "requestId": "30361206-c19c-4260-894d-14433d37a443",
    "identity": {
      "cognitoIdentityPoolId": None,
      "accountId": None,
      "cognitoIdentityId": None,
      "caller": None,
      "sourceIp": "54.174.62.149",
      "principalOrgId": None,
      "accessKey": None,
      "cognitoAuthenticationType": None,
      "cognitoAuthenticationProvider": None,
      "userArn": None,
      "userAgent": "HubSpot Connect 2.0 (http://dev.hubspot.com/) (namespace: WebhooksPlatformExecution) - WebhooksPlatformService-userweb",
      "user": None
    },
    "domainName": "k5bqz34xfi.execute-api.us-east-1.amazonaws.com",
    "apiId": "k5bqz34xfi"
  },
  "body": "{\"email\":\"jaimematarazzo+webhooktest3@gmail.com\",\"First_Name\":\"Jaime\",\"Last_name\":\"Test\",\"Course_Id\":\"course-v1:ALEPH+DIG-AD-SP+ENG01\",\"Password\":123456}",
  "isBase64Encoded": False
}
for i in range(1,2):
    r = lambda_handler(event, None)
    print(i, r)
    if r.get('statusCode') != 200:
        break