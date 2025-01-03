REST API Client for Open edX |CI|_ |Codecov|_
=============================================
.. |CI| image:: https://github.com/aulasneo/openedx-api-client/workflows/Python%20CI/badge.svg?branch=master
.. _CI: https://github.com/aulasneo/openedx-rest-api-client/actions?query=workflow%3A%22Python+CI%22

.. |Codecov| image:: https://codecov.io/github/aulasneo/openedx-api-client/coverage.svg?branch=master
.. _Codecov: https://codecov.io/github/aulasneo/openedx-rest-api-client?branch=master

The REST API client for Open edX REST API allows users to communicate with various edX REST APIs.
It is based on https://github.com/edx/edx-rest-api-client, whith a few differences:

- It does not depend on Django
- What is called 'the client' in edX's version is now called 'session'.
- As the edX's version relies on Django's cache, now the token is stored in memory under the scope of the session object
- The client here encompasses the session, and one function per REST API entry point

Part of the code is also taken from Opencraft's `implementation of the openedx client`_.

.. _implementation of the openedx client: https://gist.github.com/bradenmacdonald/930c7655dca32dc648af9cb0aed4a7c5


Testing
-------
    $ make validate


Usage
~~~~~

The ``OpenedxRESTAPIClient`` object starts a session with the LMS and provides methods to access the Open edX endpoints.

.. code-block:: python

    from openedx_rest_api_client.client import OpenedxRESTAPIClient
  
    client_id = 'my_client_id'
    client_secret = 'my_client_secret'
    lms_url = 'https://lms.example.com'

    # create client
    client = OpenedxRESTAPIClient(lms_url, client_id, client_secret)

    # get a list of all courses
    courses = client.list_all_courses()

Function Reference
------------------

list_all_courses
~~~~~~~~~~~~~~~~
Get the full list of courses visible to the requesting user.
Calls the /api/courses/v1/courses LMS endpoint

Args:

- org: filter by organization

Returns:

- List of dict in the form:

.. code-block::

        [
           {
              "blocks_url": "https://lms.example.com/api/courses/v1/blocks/?course_id=course-v1%3A<org>%2B<code>%2B<edition>",
              "effort":"01:00",
              "end":"None",
              "enrollment_start":"None",
              "enrollment_end":"None",
              "id":"course-v1:<org>+<code>+<run>",
              "media":{
                 "course_image":{
                    "uri":"<img path>"
                 },
                 "course_video":{
                    "uri":"None"
                 },
                 "image":{
                    "raw":"<img url>",
                    "small":"<img url>",
                    "large":"<img url>"
                 }
              },
              "name":"Course name",
              "number":"<edition>",
              "org":"<org>",
              "short_description":"",
              "start":"2018-01-11T00:00:00Z",
              "start_display":"11 de Enero de 2018",
              "start_type":"timestamp",
              "pacing":"instructor",
              "mobile_available":true,
              "hidden":false,
              "invitation_only":false,
              "course_id":"course-v1:<org>+<code>+<edition>"
           },
           ...
        ]

change_enrollment
~~~~~~~~~~~~~~~~~

Enroll or unenroll (depending on the value of action) the list of emails in the list of courses.
Calls the /api/bulk_enroll/v1/bulk_enroll/ LMS endpoint

Args:

- emails: list of emails to enroll
- courses: list of course ids to enroll
- action: can be 'enroll' or 'unenroll'
- url: url of the LMS (base or site). If not specified, uses the base url of the session. Defaults to the LMS base.
- auto_enroll: if true, the users will be automatically enrolled as soon as they register. Defaults to true.
- email_students: if true, an email will be sent with the update. Defaults to true.
- cohorts: List of cohort names to add the students to.

Returns:

dict in the form:

.. code-block::

    {
       "action":"enroll",
       "courses":{
          "course-v1:ORG+CODE+EDITION":{
             "action":"enroll",
             "results":[
                {
                   "identifier":"mail@example.com",
                   "after":{
                      "enrollment":true,
                      "allowed":false,
                      "user":true,
                      "auto_enroll":false
                   },
                   "before":{
                      "enrollment":false,
                      "allowed":false,
                      "user":true,
                      "auto_enroll":false
                   }
                },
                ...
             ],
             "auto_enroll":true
          },
          ...
       },
       "email_students":true,
       "auto_enroll":true
    }

Account validation
~~~~~~~~~~~~~~~~~~

Validates the account registration form. Calls the `/api/user/v1/validation/registration` API endpoint.

Args:

* url: url of the LMS (base or site). If not specified, uses the base url of the session. Defaults to the LMS base.
* \*\*kwargs: dict with form parameters to validate. E.g.:

.. code-block::

    {
        email=<email>,
        username=<username>,
        name=<name>,
        password=<password>,
        honor_code=<honor_code>,
        terms_of_service=<terms_of_service>,
    }

Returns:
dict in the form:

.. code-block::

    {
        'validation_decisions': {
            <field name>: <validation result, or empty if success>,
            ...
        },
        'username_suggestions': [<username suggestions * 3>]
    }


Account registration
~~~~~~~~~~~~~~~~~~~~

Registers a new user account. Calls the `/api/user/v1/account/registration/` API endpoint.

Args:

* email: email to register
* username: username to register
* name: full name of the user
* password: password
* url: url of the LMS (base or site). If not specified, uses the base url of the session.
        Defaults to the LMS base.

Additional default fields accepted:

* name: full name of the user
* level_of_education \*: one of:
    * 'p': 'Doctorate'
    * 'm': "Master's or professional degree"
    * 'b': "Bachelor's degree"
    * 'a': "Associate degree"
    * 'hs': "Secondary/high school"
    * 'jhs': "Junior secondary/junior high/middle school"
    * 'el': "Elementary/primary school"
    * 'none': "No formal education"
    * 'other': "Other education"
* gender \*: can be 'm', 'f', or 'o'
* mailing_address *
* city *
* country: ISO3166-1 two letters country codes as used in django_countries.countries *
* goals *
* year_of_birth \*: numeric 4-digit year of birth
* honor_code \*: Bool. If mandatory and not set will not create the account.
* terms_of_service \*: Bool. If unset, will be set equally to honor_code
* marketing_emails_opt_in \*: Bool. If set, will add a is_marketable user attribute (see Student > User Attributes in Django admin)
* provider: Oauth2 provider information
* social_auth_provider: Oauth2 provider information

\* Can be set as hidden, optional or mandatory in REGISTRATION_EXTRA_FIELDS setting.


Returns:
Dict with the form:

- If successful:

.. code-block::

    {
        'success': True,
        'redirect_url': <redirection url to finish the authorization and go to the dashboard>
    }

- If error:

.. code-block::

    {
        <field name>: [
            {'user_message': <error message>}
        ]
        'error_code': <error code>,
        'username_suggestions': [<username suggestions> * 3]
    }

How to Contribute
-----------------

To contribute, please send a message to `andres@aulasneo.com`_

.. _andres@aulasneo.com: mailto:andres@aulasneo.com
